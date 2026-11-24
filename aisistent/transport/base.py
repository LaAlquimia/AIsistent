from abc import ABC, abstractmethod


class Transport(ABC):
    @abstractmethod
    def connect(self, **kwargs) -> None:
        ...

    @abstractmethod
    def disconnect(self) -> None:
        ...

    @abstractmethod
    def capture(self) -> tuple[float, str]:
        ...

    @abstractmethod
    def click(self, x_percent: float, y_percent: float) -> dict:
        ...

    @abstractmethod
    def send_key(self, key: str) -> dict:
        ...

    @abstractmethod
    def type_text(self, text: str) -> dict:
        ...
