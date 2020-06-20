from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Tuple, Type, cast, ClassVar

import attr
from attr import Attribute

from ics.component import Component
from ics.converter.base import AttributeConverter, GenericConverter
from ics.grammar import Container
from ics.types import ContainerItem, ContextDict
from ics.utils import check_is_instance

__all__ = [
    "MemberComponentConverter",
    "ComponentMeta",
]


@attr.s(frozen=True)
class MemberComponentConverter(AttributeConverter):
    meta: "ComponentMeta" = attr.ib()

    @property
    def filter_ics_names(self) -> List[str]:
        return [self.meta.component_type.NAME]

    def populate(self, component: Component, item: ContainerItem, context: ContextDict) -> bool:
        assert isinstance(item, Container)
        self._check_component(component, context)
        self.set_or_append_value(component, self.meta.load_instance(item, context))
        return True

    def serialize(self, parent: Component, output: Container, context: ContextDict):
        self._check_component(parent, context)
        extras = self.get_extra_params(parent)
        if extras:
            raise ValueError("ComponentConverter %s can't serialize extra params %s", (self, extras))
        for value in self.get_value_list(parent):
            # don't force self.meta for serialization, but use the meta registered for the concrete type of value
            output.append(value.to_container(context))
        context.pop("DTSTART", None)  # TODO maybe better use a finalize equivalent for serialize?


@attr.s(frozen=True)
class ComponentMeta(object):
    BY_TYPE: ClassVar[Dict[Type, "ComponentMeta"]] = {}

    component_type: Type[Component] = attr.ib()

    converters: Tuple[GenericConverter, ...]
    converter_lookup: Dict[str, Tuple[GenericConverter]]

    def __attrs_post_init__(self):
        object.__setattr__(self, "converters", tuple(self.find_converters()))
        converter_lookup = defaultdict(list)
        for converter in self.converters:
            for name in converter.filter_ics_names:
                converter_lookup[name].append(converter)
        object.__setattr__(self, "converter_lookup", {k: tuple(vs) for k, vs in converter_lookup.items()})

    def find_converters(self) -> Iterable[AttributeConverter]:
        converters = cast(Iterable[AttributeConverter], filter(bool, (
            AttributeConverter.get_converter_for(a) for a in attr.fields(self.component_type))))
        return sorted(converters, key=lambda c: c.priority)

    def __call__(self, attribute: Attribute):
        return MemberComponentConverter(attribute, self)

    def load_instance(self, container: Container, context: Optional[ContextDict] = None):
        instance = self.component_type()
        self.populate_instance(instance, container, context)
        return instance

    def populate_instance(self, instance: Component, container: Container, context: Optional[ContextDict] = None):
        if container.name != self.component_type.NAME:
            raise ValueError("container isn't an {}".format(self.component_type.NAME))
        check_is_instance("instance", instance, (self.component_type, MutablePseudoComponent))
        if not context:
            context = ContextDict(defaultdict(lambda: None))

        self._populate_attrs(instance, container, context)

    def _populate_attrs(self, instance: Component, container: Container, context: ContextDict):
        for line in container:
            consumed = False
            for conv in self.converter_lookup.get(line.name, []):
                if conv.populate(instance, line, context):
                    consumed = True
            if not consumed:
                instance.extra.append(line)

        for conv in self.converters:
            conv.finalize(instance, context)

    def serialize_toplevel(self, component: Component, context: Optional[ContextDict] = None):
        check_is_instance("instance", component, self.component_type)
        if not context:
            context = ContextDict(defaultdict(lambda: None))
        container = Container(self.component_type.NAME)
        self._serialize_attrs(component, context, container)
        return container

    def _serialize_attrs(self, component: Component, context: ContextDict, container: Container):
        for conv in self.converters:
            conv.serialize(component, container, context)
        container.extend(component.extra)


class MutablePseudoComponent(object):
    def __init__(self, comp: Type[Component]):
        object.__setattr__(self, "NAME", comp.NAME)
        object.__setattr__(self, "extra", Container(comp.NAME))
        object.__setattr__(self, "extra_params", {})
        data = {}
        for field in attr.fields(comp):
            if not field.init:
                continue
            elif isinstance(field.default, attr.Factory):  # type: ignore[arg-type]
                assert field.default is not None
                if field.default.takes_self:
                    data[field.name] = field.default.factory(self)
                else:
                    data[field.name] = field.default.factory()
            elif field.default != attr.NOTHING:
                data[field.name] = field.default
        object.__setattr__(self, "_MutablePseudoComponent__data", data)

    def __getattr__(self, name: str) -> Any:
        return self.MutablePseudoComponent_data[name]

    def __setattr__(self, name: str, value: Any) -> None:
        assert name not in ("NAME", "extra", "extra_params")
        self.MutablePseudoComponent_data[name] = value

    def __delattr__(self, name: str) -> None:
        del self.MutablePseudoComponent_data[name]

    @staticmethod
    def from_container(*args, **kwargs):
        raise NotImplementedError()

    @staticmethod
    def populate(*args, **kwargs):
        raise NotImplementedError()

    @staticmethod
    def to_container(*args, **kwargs):
        raise NotImplementedError()

    @staticmethod
    def serialize(*args, **kwargs):
        raise NotImplementedError()

    @staticmethod
    def strip_extras(*args, **kwargs):
        raise NotImplementedError()

    @staticmethod
    def clone(*args, **kwargs):
        raise NotImplementedError()


class ImmutableComponentMeta(ComponentMeta):
    def load_instance(self, container: Container, context: Optional[ContextDict] = None):
        pseudo_instance = cast(Component, MutablePseudoComponent(self.component_type))
        self.populate_instance(pseudo_instance, container, context)
        instance = self.component_type(**{k.lstrip("_"): v for k, v in pseudo_instance.MutablePseudoComponent_data.items()})  # type: ignore
        instance.extra.extend(pseudo_instance.extra)
        instance.extra_params.update(pseudo_instance.extra_params)
        return instance