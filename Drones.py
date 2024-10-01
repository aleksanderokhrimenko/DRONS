
# Паттерн "Команда" (Command Pattern)
from abc import ABC, abstractmethod
import logging
import concurrent.futures
import time

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Класс для управления дроном
class IDrone(ABC):
    def __init__(self):
        self.orientation = 0  # текущая ориентация дрона в градусах



    @abstractmethod
    def arm(self):
        pass

    @abstractmethod
    def takeoff(self):
        pass

    @abstractmethod
    def land(self):
        pass

    @abstractmethod
    def rotate(self, degree: int):
        pass

    @abstractmethod
    def rotate_cancel(self, degree: int):
        pass

    @abstractmethod
    def change_altitude(self, altitude: int):
        pass

    @abstractmethod
    def drop_payload(self):
        pass


class Drone(IDrone):
    def __init__(self, id, model):
        super(Drone, self).__init__()
        self.id = id
        self.model = model

    def __str__(self):
        return f'{self.id}, {self.model}'

    def commands(self, msg):
        commands = {'land': self.land,
                    'takeoff': self.takeoff,
                    'arm': self.arm
                    }
        commands[msg]()

    def arm(self):
        # Разблокировка управления и взлет

        logging.info("Выполнено армирование")

    def takeoff(self):
        # Взлет до высоты 3 метра
        print(f'Дрон {self.id} взлетает!')
        logging.info("Взлет до высоты 3 метра")

    def land(self):
        print(f'Дрон {self.id} идет на посадку!')
        logging.info('Дрон: приземлился')

    def rotate(self, degree: float, duration: float):
        # Метод для поворота дрона на заданное количество градусов
        print(f'Дрон: поворот на {degree} градусов')
        # Изменяем ориентацию дрона и приводим значение к диапазону 0-359 градусов
        self.orientation = (self.orientation + degree) % 360


    def rotate_cancel(self, degree: float, duration: float):
        # Метод для отмены поворота дрона (поворот в обратную сторону)
        self.rotate(-degree, duration)

    def change_altitude(self, altitude: int):
        # Метод для изменения высоты полета дрона
        logging.info(f'Дрон: набор высоты до {altitude} м')


    def drop_payload(self):
        # Метод для сброса нагрузки с дрона
        print("Дрон: сброс нагрузки")


# Интерфейс команды (абстрактный класс)
class ICommand(ABC):
    def __init__(self, IDrone: IDrone):
        # Сохраняем ссылку на объект дрона
        self._IDrone = IDrone

    @abstractmethod
    def execute(self):
        # Абстрактный метод для выполнения команды
        pass

    @abstractmethod
    def undo(self):
        # Абстрактный метод для отмены команды
        pass

    def reset(self):
        # Сброс параметров команды перед возвратом в пул
        pass

# Команда для взлета
class TakeoffCommand(ICommand):
    def execute(self):
        # Выполнение команды взлета
        self._IDrone.takeoff()

    def undo(self):
        # Отмена взлета (в данном случае не реализована)
        pass

# Команда для приземления
class LandCommand(ICommand):
    def execute(self):
        # Выполнение команды приземления
        self._IDrone.land()

    def undo(self):
        # Отмена приземления (в данном случае не реализована)
        pass

# Команда для сброса нагрузки
class DropPayloadCommand(ICommand):
    def execute(self):
        # Выполнение команды сброса нагрузки
        self._IDrone.drop_payload()

    def undo(self):
        # Отмена сброса нагрузки (в данном случае не реализована)
        pass

# Команда для изменения высоты полета
class ChangeAltitudeCommand(ICommand):
    def __init__(self, IDrone: IDrone, altitude: int):
        # Инициализация команды с заданной высотой
        super().__init__(IDrone)
        self._altitude = altitude

    def execute(self):
        # Выполнение команды изменения высоты
        self._IDrone.change_altitude(self._altitude)

    def undo(self):
        # Отмена изменения высоты (в данном случае не реализована)
        pass

# Команда для поворота дрона
class RotateCommand(ICommand):
    def __init__(self, IDrone: IDrone, degree: int):
        # Инициализация команды с заданным углом поворота
        super().__init__(IDrone)
        self._degree = degree

    def execute(self):
        # Выполнение команды поворота
        self._IDrone.rotate(self._degree)

    def undo(self):
        # Отмена поворота (поворот в обратную сторону)
        self._IDrone.rotate_cancel(self._degree)


# Класс Invoker, управляющий выполнением команд
class Invoker:
    def __init__(self):
        self._commands = []  # Очередь команд для выполнения
        self._executed_commands = []  # Список выполненных команд

    def add_command(self, command: ICommand):
        # Добавление команды в очередь
        self._commands.append(command)

    def execute(self):
        # Выполнение всех команд в очереди
        for command in self._commands:
            command.execute()
            self._executed_commands.append(command)
        # Очистка очереди после выполнения
        self._commands.clear()

    def undo(self):
        # Отмена последней выполненной команды
        if self._executed_commands:
            last_command = self._executed_commands.pop()
            last_command.undo()
        else:
            print("Дрон отменил все действия")


class ObjectsPool:
    def __init__(self, obj, size):
        self._pool = [obj() for _ in range(size)]
        self._used = []

    def acquire(self):
        if len(self._pool) == 0:
            raise IndexError('Нет доступных объектов в пуле')
        obj = self._pool.pop()
        self._used.append(obj)
        return obj

    def release(self, obj):
        obj.reset()
        self._used.remove(obj)
        self._pool.append(obj)

class CommandPool:
    def __init__(self, command_type, *args, **kwargs):
        self.command = None
        if command_type == "rotate":
            self.command = RotateCommand(*args, **kwargs)
        elif command_type == "altitude":
            self.command = ChangeAltitudeCommand(*args, **kwargs)

def perform_command(pool, command_type, *args, **kwargs):
    command_pool = None
    try:
        command_pool = pool.acquire()
        command_pool = command_pool(command_type, *args, **kwargs)
        command_pool.command.execute()
    finally:
        if command_pool is not None:
            pool.release(command_pool)


if __name__ == '__main__':
    drone1 = Drone('drn001', 'DJI')
    drone2 = Drone('drx002', 'DJI')
    drone3 = Drone('dprn003', 'DJI')
    print(drone1, drone2, drone3)

    drone2.takeoff()



