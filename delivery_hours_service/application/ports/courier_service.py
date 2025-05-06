from abc import ABC, abstractmethod

from delivery_hours_service.domain.models.delivery_window import WeeklyDeliveryWindow


class CourierServicePort(ABC):
    @abstractmethod
    async def get_delivery_hours(self, city: str) -> WeeklyDeliveryWindow:
        """
        Retrieves delivery hours for a city from the Courier Service and
        converts them to the domain representation.

        Raises:
            NotImplementedError: This method must be implemented by concrete adapters
        """
        raise NotImplementedError
