import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import DEVELOPER_ID, MIN_AGE, TOKEN
from message_texts import (
    BAD_BIRTH_DATE_MESSAGE,
    END_MESSAGE,
    GOOD_BIRTH_DATE_MESSAGE,
    HELLO_MESSAGE,
    NAME_OK_MESSAGE,
)
from models import Form

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """
    Handles the /start command.
    Clears user state and starts the name collection process.
    """
    await state.clear()
    await message.answer(HELLO_MESSAGE)
    await state.set_state(Form.waiting_for_name)
    logging.info("Новый пользователь: %s", message.from_user.username)


@router.message(Form.waiting_for_name)
async def name_step(message: Message, state: FSMContext):
    """
    Processes the user's name input.
    Stores the full name in the state, validates format, and proceeds to next step.
    """
    try:
        name_from_message = message.text.split()[1]
        await state.update_data(userid=message.from_user.id)
        await state.update_data(user=message.from_user.username)
        await state.update_data(name=message.text)
        await message.answer(f"Отлично, {name_from_message}! {NAME_OK_MESSAGE}")
        await state.set_state(Form.waiting_for_birth_date)
    except IndexError:
        await message.answer(
            "Укажите ФИО через пробел (например: Иванов Иван Иванович)"
        )


@router.message(Form.waiting_for_birth_date)
async def birth_date_step(message: Message, state: FSMContext):
    """
    Processes the user's birth date input.
    Calculates age and validates if it meets the minimum requirement.
    """
    date_str = message.text
    try:
        birth_date = datetime.strptime(date_str, "%d.%m.%Y")
        today = datetime.today()
        age = today.year - birth_date.year - (
            (today.month, today.day) < (birth_date.month, birth_date.day)
        )
        logging.info(
            "Возраст пользователя: %s - %s", message.from_user.username, age
        )
        await state.update_data(birth_date=date_str)
        await state.update_data(age=age)

        if age >= MIN_AGE:
            await message.answer(GOOD_BIRTH_DATE_MESSAGE)
            await state.set_state(Form.waiting_for_number)
        else:
            await message.answer(BAD_BIRTH_DATE_MESSAGE)
            await state.clear()

    except ValueError:
        await message.answer(
            "Неверный формат даты. Пожалуйста, используйте формат ДД.ММ.ГГГГ."
        )


@router.message(Form.waiting_for_number)
async def number_step(message: Message, state: FSMContext):
    """
    Processes the user's phone number input.
    Sends the collected data to the developer with accept/decline options.
    """
    await state.update_data(number=message.text)
    data = await state.get_data()

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Принять ✅", callback_data=f"accept_{data['userid']}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Отклонить ❌", callback_data=f"decline_{data['userid']}"
                )
            ],
        ]
    )

    await message.answer(END_MESSAGE)
    text_data = (
        f"Пользователь: @{data['user']}\n"
        f"Имя: {data['name']}\n"
        f"Дата рождения: {data['birth_date']} ({data['age']})\n"
        f"Телефон: {data['number']}\n"
    )

    try:
        await message.bot.send_message(
            chat_id=DEVELOPER_ID,
            text=f"✅ Новая заявка\n{text_data}",
            reply_markup=markup,
        )
    except Exception as err:
        logging.error(
            "Ошибка при отправке сообщения администратору: %s Текст заявки: %s",
            err,
            text_data,
        )

    await state.clear()


@router.callback_query(F.data.startswith("accept"))
async def accept(callback: CallbackQuery):
    """
    Handles acceptance of an application by the admin.
    Sends a token to the user and notifies the admin.
    """
    user_id = callback.data.split("_")[1]
    new_token = "ABRAKADABRA-sd-125xx-a"

    reply_user_text = (
        "Поздравляем, Ваша заявка принята!\n"
        f"Ваш токен: `{new_token}`\n\n"
        "Для начала работы зайдите на [сайт](https://google.com) и введите токен."
    )

    reply_admin_text = f"Токен: `{new_token}`"

    await callback.answer()
    await callback.message.answer(
        reply_admin_text,
        parse_mode=ParseMode.MARKDOWN,
    )

    try:
        await callback.bot.send_message(
            chat_id=user_id,
            text=reply_user_text,
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as err:
        logging.error(
            "Ошибка при отправке сообщения пользователю: %s Текст сообщения: %s",
            err,
            reply_user_text,
        )


@router.callback_query(F.data.startswith("decline_"))
async def decline(callback: CallbackQuery):
    """
    Handles rejection of an application by the admin.
    Sends a rejection message to the user.
    """
    user_id = callback.data.split("_")[1]

    await callback.answer()
    await callback.message.answer("Заявка отклонена")

    try:
        await callback.bot.send_message(
            chat_id=user_id,
            text="Сожалеем, но Ваша заявка отклонена!",
        )
    except Exception as err:
        logging.error("Ошибка при отправке сообщения пользователю: %s", err)


async def main():
    """
    Main entry point to start the bot.
    Includes the router and starts polling.
    """
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
