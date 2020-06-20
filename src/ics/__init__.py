from .alarm import *
from .alarm import __all__ as all_alarms
from .attendee import Attendee, Organizer
from .component import Component
from .event import Event
from .geo import Geo
from .grammar import Container, ContentLine
from .icalendar import Calendar
from .rrule import rrule_eq  # ensure the monkey-patching is done
from .timespan import EventTimespan, Timespan, TodoTimespan
from .todo import Todo


def initialize_converters():
    # order is very important here:
    # 1) all simple value type converters
    from ics.valuetype import base
    from ics.valuetype import generic
    from ics.valuetype import text
    from ics.valuetype import datetime
    from ics.valuetype import special

    # 2) all relatively simple attribute converters and advanced component converters
    from ics.converter import base
    from ics.converter import value
    from ics.converter import special
    from ics.converter import timespan
    from ics.converter import timezone

    # 3) converters for all remaining component subclasses
    from ics.converter.component import ComponentMeta
    ComponentMeta.BY_TYPE[Event] = ComponentMeta(Event)
    ComponentMeta.BY_TYPE[Todo] = ComponentMeta(Todo)

    # 4) the converter for the calendar
    from ics.converter import calendar

    global initialize_converters
    initialize_converters = lambda: None


def dump_converters():
    from pprint import pprint
    from ics.valuetype.base import ValueConverter
    print("ValueConverter.BY_TYPE:")
    pprint(ValueConverter.BY_TYPE)
    print("ValueConverter.BY_NAME:")
    pprint(ValueConverter.BY_NAME)
    from ics.converter.base import AttributeConverter
    print("AttributeConverter.BY_TYPE:")
    pprint(AttributeConverter.BY_TYPE)
    from ics.converter.component import ComponentMeta
    print("ComponentMeta.BY_TYPE:")
    pprint(ComponentMeta.BY_TYPE)
    print("Component.SUBTYPES:")
    pprint(Component.SUBTYPES)


__all__ = [
    *all_alarms,
    "Attendee",
    "Organizer",
    "Component",
    "Event",
    "Geo",
    "Container",
    "ContentLine",
    "Calendar",
    "Timespan",
    "EventTimespan",
    "TodoTimespan",
    "Todo",
    "__version__"
]

__version__ = "0.8.0-dev"