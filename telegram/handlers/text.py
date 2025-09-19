from aiogram import Router, F, types

router = Router()

@router.message(F.text)
async def text_message_handler(message: types.Message):
    await message.answer("Получено. Обрабатываю запрос...")