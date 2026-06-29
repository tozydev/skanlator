import asyncio
from typing import TypeVar, Type, Callable, Awaitable, Dict, List, Any

T = TypeVar('T')


class EventBus:
    def __init__(self) -> None:
        self._handlers: Dict[Type[Any], List[Callable[[Any], Awaitable[None]]]] = {}

    def subscribe(self, event_type: Type[T], handler: Callable[[T], Awaitable[None]]) -> None:
        """Subscribe a handler to be notified when a specific event type is published."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)  # type: ignore

    def unsubscribe(self, event_type: Type[T], handler: Callable[[T], Awaitable[None]]) -> None:
        """Unsubscribe a handler from a specific event type."""
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)  # type: ignore
            except ValueError:
                pass

    async def publish(self, event: Any) -> None:
        """Publish an event asynchronously to all subscribed handlers."""
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            return
        await asyncio.gather(*(handler(event) for handler in handlers))
