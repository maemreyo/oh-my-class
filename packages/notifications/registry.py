"""Channel registry — add new channels here, zero other changes needed."""
from packages.notifications.channels.sse import SSEChannel
from packages.notifications.channels.telegram import TelegramChannel
from packages.notifications.dispatcher import NotificationDispatcher


def build_dispatcher(stream_manager=None) -> NotificationDispatcher:
    """Build dispatcher with all enabled channels."""
    return NotificationDispatcher(channels=[
        SSEChannel(stream_manager=stream_manager),
        TelegramChannel(),
        # EmailChannel(),  # uncomment when configured
    ])
