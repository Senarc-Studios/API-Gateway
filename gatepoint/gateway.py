import uvicorn
import aiohttp
import requests

from .interaction import (Interaction,
    CommandInteraction, ButtonInteraction, MenuInteraction,
    SubCommandInteraction, SubCommandGroupInteraction)
from .chunks.chunk import Chunk
from .option import CommandOption

from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

from fastapi import FastAPI, Request, HTTPException

from typing import Callable, Any, List, Optional

def output(content, type_ = None):
    if type_ == "ERROR":
        return print(f"ERR: {content}")

    elif type_ == "WARNING":
        return print(f"WARN: {content}")

    return print(f"INFO: {content}")

class Bot:
    def __init__(self, json: dict):
        setattr(self, "id", json["id"])
        setattr(self, "avatar", json["avatar"])
        setattr(self, "username", json["username"])
        setattr(self, "discriminator", json["discriminator"])

class GatewayClient:
    def __init__(
        self,
        secret_key: str,
        public_key: str,
        token: str,
        api_version: Optional[int] = 10,
        port: Optional[int] = 80,
        verbose: Optional[bool] = False
    ):
        """## GatewayClient
        The main class for building your Interaction API for Discord.

        Args:
            `secret_key` (`str`): The Discord Application's Secret Key.
            `public_key` (`str`): The Discord Application's Public Key.
            `token` (`str`): Bot's token.
            `api_version` (`Optional[int]`): The API version your requests will go through. Defaults to `10`.
            `port` (`Optional[int]`): The port your API will be hosted in. Defaults to `80`.
            `verbose` (`Optional[bool]`): Enable to see errors or requests from discord. Defaults to `False`.

        Raises:
            ValueError: Invalid token provided.
        """
        self.discord_prefix = f"https://discord.com/api/v{api_version}"
        self.secret_key = secret_key
        self.public_key = public_key
        self.token = token
        self.port = port
        self.verbose: bool = verbose
        self.session: Any = None

        self.autocomplete: dict = {}
        self.buttons: dict = {}
        self.commands: dict = {}
        self.events: dict = {}
        self.interactions: dict = {}
        self.menus: dict = {}
        self.subcommands = {}

        response = requests.get(
            f"{self.discord_prefix}/users/@me",
            headers = {
                "Authorization": f"Bot {self.token}",
                "Content-Type": "application/json",
                "User-Agent": "GatePoint API Gateway"
            }
        )
        if response.status_code == 200:
            self.bot = Bot(response.json())

        else:
            raise ValueError("Invalid token provided.")

    async def request(self, method: str, endpoint: str, json: dict = None) -> dict:
        """## Discord API Request
        Sends a request to the Discord API.

        Args:
            method (str): HTTP methods such as `GET`, `POST`, `PUT`, `PATCH`, `DELETE`.
            endpoint (str): Discord API endpoint.
            json (dict, optional): The data you want in the request. Defaults to None.

        Returns:
            dict: Response JSON from Discord API.
        """
        async with aiohttp.ClientSession(
            headers = {
                "Authorization": f"Bot {self.token}",
                "Content-Type": "application/json",
                "User-Agent": "GatePoint API Gateway"
            }
        ) as session:
            async with session.request(
                method,
                f"{self.discord_prefix}{endpoint}",
                json = json
            ) as response:
                return await response.json()

    def command(
        self,
        name: str,
        description: str = None,
        guild_ids: List[Snowflake] = None,
        options: List[dict] = None,
        dm_permission: bool = True,
        default_permission: bool = True
    ):
        """## Command Decorator
        Slash Command that can be used in a Discord Server.

        Args:
            `name` (`str`): Name of command.
            `description` (`str`): Description of command. 
            `guild_ids` (`Optional[List[Snowflake]]`): List of guild IDs to register command to. Defaults to `None`.
            `options` (`Optional[list]`): Other options within the command. Defaults to `[]`.
            `dm_permission` (`Optional[bool]`): Whether the command is enabled in DMs. Defaults to `True`.
            `default_permission` (`Optional[bool]`): Whether the command is enabled by default when the app is added to a guild. Defaults to `True`.
        """
        def decorator(func: Callable):
            interaction = CommandInteraction(
                name = name,
                description = description,
                guild_ids = guild_ids,
                options = options,
                dm_permission = dm_permission,
                default_permission = default_permission
            )
            self.commands[interaction.name] = func
            if interaction.guild_only:
                for id_ in interaction.guild_ids:
                    asyncio.run(
                        self.request(
                            "POST",
                            f"/applications/{self.bot.id}/guilds/{id_}/commands",
                            json = interaction.register_json
                        )
                    )

            else:
                asyncio.run(
                    self.request(
                        "POST",
                        f"/applications/{self.bot.id}/commands",
                        json = interaction.register_json
                    )
                )
            return func
        return decorator

    def button(self, custom_id: str):
        """## Button Decorator
        Button that can be used in a Discord Bot.

        Args:
            `custom_id` (`str`): Custom ID of button.
        """
        def decorator(func: Callable):
            interaction = ButtonInteraction(custom_id = custom_id)
            self.buttons[interaction.custom_id] = func
            return func
        return decorator

    def menu(self, custom_id: str):
        """## Menu Decorator
        Menu that can be used in a Discord Bot.

        Args:
            `custom_id` (`str`): Custom ID of menu.
        """
        def decorator(func: Callable):
            interaction = MenuInteraction(custom_id = custom_id)
            self.menus[interaction.custom_id] = func
            return func
        return decorator

    def on(self, event: str):
        """## Event Decorator
        Events that are fired on your Discord Bot.

        Args:
            `event` (`str`): Event name.
        """
        def decorator(func: Callable):
            event_list = self.events.get(event).append(func) if self.events.get(event) else [func]
            self.events[event] = event_list

            return func
        return decorator

    def run(self):
        """## Run
        Runs the Interaction API.

        ## Troubleshooting
        - If you require assistance/help, you may contact us at [Discord](https://discord.gg/5YY3W83YWg).
        - If your bot stops as soon as you run it, you can view by specifying `verbose = True` in GatewayClient.
        - If you are getting an error saying that the port is already in use, you fix it by mentioning a port in GatewayClient like `port = 8000` as an argument.
        - If your bot stops responding to interactions, you can fix it by restarting the bot.
        """
        app = FastAPI()

        @app.on_event("startup")
        async def startup_event():
            output("GatePoint API Dispatched, listening for interactions.")
            for event in self.events.get("startup") or []:
                event: Callable
                await event()

        @app.get("/")
        async def index():
            return "This is a Discord Interaction API."

        @app.post("/interaction")
        async def interaction(request: Request):
            # Verify the request.
            verify_key = VerifyKey(bytes.fromhex(self.public_key))
            signature = request.headers.get("X-Signature-Ed25519")
            timestamp = request.headers.get("X-Signature-Timestamp")

            if not signature or not timestamp:
                raise HTTPException(
                    detail = 'missing request signature',
                    status_code = 401
                )

            body = (await request.body()).decode("utf-8")

            try:
                verify_key.verify(f'{timestamp}{body}'.encode(), bytes.fromhex(signature))
            except BadSignatureError:
                return HTTPException(
                    detail = 'invalid request signature',
                    status_code = 401
                )

            # Process the request.
            interaction_payload = await request.json()

            if interaction_payload["type"] == 1:
                return {
                    "type": 1
                }

            elif interaction_payload["type"] == 2:
                if interaction_payload["data"]["name"] in self.commands:
                    print(self.events)
                    for event in self.events.get("interaction_receive") or []:
                        event: Callable
                        await event(Interaction(interaction_payload))

                    for event in self.events.get("command_receive") or []:
                        event: Callable
                        await event(Interaction(interaction_payload))

                    if interaction_payload.get("data").get("options"):
                        input_tuple = ()
                        for option in interaction_payload["data"]["options"]:
                            input_tuple = input_tuple.__add__((option["value"]))

                        return await self.commands[interaction_payload["data"]["name"]](Interaction(interaction_payload), *input_tuple)

                    else:
                        return await self.commands[interaction_payload["data"]["name"]](Interaction(interaction_payload))

                return {
                    "type": 4,
                    "data": {
                        "content": "This command is not registered with Interaction Gateway API.",
                        "flags": 64
                    }
                }

            elif interaction_payload["type"] == 3:
                print(interaction_payload["data"])
                if interaction_payload["data"]["component_type"] in (3, 4, 5, 6, 7, 8):
                    value = interaction_payload["data"]["values"][0] if interaction_payload["data"]["values"] else None
                    if interaction_payload["data"]["custom_id"] in self.menus:
                        for event in self.events.get("interaction_receive") or []:
                            event: Callable
                            await event(Interaction(interaction_payload))

                        for event in self.events.get("menu_select") or []:
                            event: Callable
                            await event(Interaction(interaction_payload))

                        return await self.menus[interaction_payload["data"]["custom_id"]](Interaction(interaction_payload), interaction_payload["data"]["values"])

                    return {
                        "type": 4,
                        "data": {
                            "content": "This menu is not registered with Interaction Gateway API.",
                            "flags": 64
                        }
                    }

                elif interaction_payload["data"]["custom_id"] in self.buttons:
                    for event in self.events.get("interaction_receive") or []:
                        event: Callable
                        await event(Interaction(interaction_payload))

                    for event in self.events.get("button_click") or []:
                        event: Callable
                        await event(Interaction(interaction_payload))

                    return await self.buttons[interaction_payload["data"]["custom_id"]](Interaction(interaction_payload))

                return {
                    "type": 4,
                    "data": {
                        "content": "This button is not registered with Interaction Gateway API.",
                        "flags": 64
                    }
                }

            elif interaction_payload["type"] >= 4 or interaction_payload["type"] < 12:
                return {
                    "type": 4,
                    "data": {
                        "content": "This interaction is not yet supported by Interaction Gateway API.",
                        "flags": 64
                    }
                }

            else:
                raise HTTPException(detail = "Interaction not recognised by Interaction Gateway API.", status_code = 400)

        uvicorn.run(
            app,
            host = "127.0.0.1",
            port = self.port
        ) if self.verbose else uvicorn.run(
            app,
            log_level = "critical",
            host = "127.0.0.1",
            port = self.port
        )