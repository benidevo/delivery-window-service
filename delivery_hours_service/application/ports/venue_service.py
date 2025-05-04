from abc import ABC, abstractmethod

from delivery_hours_service.domain.models.delivery_window import WeeklyDeliveryWindow


class VenueServicePort(ABC):
    @abstractmethod
    async def get_opening_hours(self, venue_id: str) -> WeeklyDeliveryWindow:
        """
        Retrieves opening hours for a venue from the Venue Service and
        converts them to the domain representation.

        Raises:
            NotImplementedError: This method must be implemented by concrete adapters
        """
        raise NotImplementedError
