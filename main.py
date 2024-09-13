import logging
import subprocess
import os
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
)
from telegram.ext import filters

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Отправь мне 📹 видео — я сделаю из него кружок. Я обрежу видео, если оно будет длиннее 60 секунд."
    )

async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    message = update.message

    video_file = None
    input_file = None
    output_file = None

    if message.video:
        video_file = message.video
    elif message.document and message.document.mime_type.startswith('video/'):
        video_file = message.document

    if not video_file:
        await update.message.reply_text("Пожалуйста, отправьте видео файл.")
        return

    # Проверяем размер входящего файла
    max_input_size = 20 * 1024 * 1024  # 20 МБ
    if video_file.file_size > max_input_size:
        await update.message.reply_text("Размер видео превышает 20 МБ. Пожалуйста, отправьте видео меньшего размера.")
        return

    # **Отправляем сообщение пользователю**
    await update.message.reply_text("Всё отлично, подождите буквально минуту!")

    try:
        # Скачиваем видео
        video = await video_file.get_file()
        input_file = f"{video.file_id}.mp4"
        output_file = f"circle_{video.file_id}.mp4"
        await video.download_to_drive(input_file)

        # Преобразуем видео с помощью FFmpeg
        command = [
            'ffmpeg', '-y', '-i', input_file,
            '-t', '60',  # Обрезает видео до 60 секунд
            '-vf', 'crop=min(iw\\,ih):min(iw\\,ih),scale=640:640',
            '-codec:a', 'aac', '-b:a', '128k',  # Улучшение качества аудио
            '-codec:v', 'libx264', '-preset', 'slow', '-crf', '20',  # Улучшение качества видео
            output_file
        ]
        subprocess.run(command, check=True)

        # Проверяем размер выходного файла
        output_file_size = os.path.getsize(output_file)
        max_output_size = 50 * 1024 * 1024  # 50 МБ

        if output_file_size > max_output_size:
            await update.message.reply_text("Не удалось сжать видео до допустимого размера.")
            return

        # Отправляем видео как видео-сообщение (кружочек)
        with open(output_file, 'rb') as video_note:
            await context.bot.send_video_note(
                chat_id=update.effective_chat.id,
                video_note=video_note
            )

        # Отправляем дополнительное сообщение с гиперссылкой
        await update.message.reply_text(
            "Благодарю за использование бота! Если хочешь узнавать больше про кино, подпишись на телеграм-канал [Тележка Киноманов](https://t.me/staskinoman)",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )

    except Exception as e:
        logger.error(f"Ошибка при обработке видео: {e}")
        await update.message.reply_text("Произошла ошибка при обработке видео.")

    finally:
        # Удаляем временные файлы, если они были созданы
        if input_file and os.path.exists(input_file):
            os.remove(input_file)
        if output_file and os.path.exists(output_file):
            os.remove(output_file)

def main():
    TOKEN = '7256463262:AAFAJgwmiH6dFPf-dNHDIMLq-u5LWJLETqg'  # Замените на ваш токен

    application = ApplicationBuilder().token(TOKEN).build()

    # Обработчик для команды /start
    application.add_handler(CommandHandler("start", start))

    # Обработчик для входящих видео
    video_filter = filters.VIDEO | filters.Document.VIDEO
    application.add_handler(MessageHandler(video_filter, video_handler))

    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()
