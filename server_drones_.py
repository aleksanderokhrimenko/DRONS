import websockets
import asyncio
import logging
import signal
import aiohttp_cors
from aiohttp import web
from websockets.exceptions import ConnectionClosedError
from Drones import *
import json


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')



drone1 = Drone('drn001', 'DJI')
drone2 = Drone('drx002', 'DJI')
drone3 = Drone('dprn003', 'DJI')

drones = [{'id': drone1.id, "name": "Lider"},
          {'id': drone2.id, "name": "Last"},
          {'id': drone3.id, "name": "Center"}
          ]

obj = {drone1.id: drone1,
       drone2.id: drone2,
       drone3.id: drone3}

drones_locks = {}

async def get_drones(request):
    return web.json_response(drones)

async def control_drone(websocket):
    client_ip = websocket.remote_address[0]
    client_port = websocket.remote_address[1]
    logging.info(f"Подключен клиент: {client_ip}:{client_port}")

    command = {
        "takeoff": "Дрон взлетает",
        "land": "Дрон приземляется",
        "hover": "Дрон зависает",
        "move_forward": "Дрон летит вперед",
        "move_back": "Дрон летит назад",
        "arm": "Армирование дрона"

    }

    selected_drone = None



    try:
        async for msg in websocket:
            if msg.startswith("selected_drone"):
                # logging.info(msg)
                drone_id = msg.split()[1]
                if drone_id not in drones_locks:
                    drones_locks[drone_id] = (client_ip, client_port)
                    selected_drone = drone_id
                    await websocket.send(f"Выбран дрон {selected_drone}. Открыт доступ к управлению")
                else:
                    client_locked = drones_locks[drone_id]
                    if client_locked == (client_ip, client_port):
                        await websocket.send(f"Вы уже управляете дроном!")
                    else:
                        await websocket.send(f"Дрон {drone_id} уже занят другим оператором")
            elif selected_drone:
                # Теперь команды отправляются без указания дрона, так как он уже выбран
                logging.info(f"{client_ip}:{client_port} отправил команду для дрона {selected_drone}: {msg}")
                obj.get(drone_id).commands(msg)
                response = command.get(msg, "Неизвестная команда")
                await websocket.send(response)
            else:
                await websocket.send("Сначала выбери дрон!")

    except ConnectionClosedError as e:
        logging.warning(f"Соединение с клиентом {client_ip}:{client_port} закрыто: {e}")
    except Exception as e:
        logging.error(f"Необработанная ошибка для {client_ip}:{client_port}: {e}")
    finally:
        if selected_drone and drones_locks.get(selected_drone) == (client_ip, client_port):
            del drones_locks[selected_drone]
            logging.info(f"Освобожден дрон {selected_drone}")



async def shutdown_server(server, signal=None):
    if signal:
        logging.info(f"Получен сигнал завершения: {signal.name}")
        server.close()
        await server.wait_closed()
        logging.info(f"Сервер завершил работу")


async def main():
    start_server = await websockets.serve(control_drone, "localhost", 8765)
    logging.info(f"Сервер запущен и ожидает подключений")

    app = web.Application()
    app.router.add_get("/drones", get_drones)

    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })

    for route in list(app.router.routes()):
        cors.add(route)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", 8081)
    await site.start()

    try:
        await start_server.wait_closed()
    except ConnectionClosedError as e:
        logging.warning(f"Соединение с клиентом закрыто: {e}")
    except Exception as e:
        logging.error(f"Необработанная ошибка: {e}")
    finally:
        start_server.close()
        await start_server.wait_closed()
        logging.error(f"Сервер завершил работу")



if __name__ == '__main__':
    asyncio.run(main())