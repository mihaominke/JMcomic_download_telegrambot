import os
import socket
import yaml
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import jmcomic
from main import all2PDF

# =============== 单实例检测 ===============
def already_running(port=9876):
    """防止多实例：绑定本地端口检测是否已有实例在运行"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", port))
        return False  # 绑定成功，说明没其他实例
    except OSError:
        return True  # 端口被占用 → 已有实例
    finally:
        s.close()

if already_running():
    print("检测到机器人已在运行，自动退出以防冲突。")
    exit(0)

# =============== 基础设置 ===============
TOKEN = os.getenv("TELEGRAM_TOKEN")
CONFIG_PATH = "config.yml"

def get_folder_size(path):
    total = 0
    for root, _, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except FileNotFoundError:
                continue
    return total

def delete_oldest_half(folder_path):
    files = []
    for root, _, names in os.walk(folder_path):
        for f in names:
            full = os.path.join(root, f)
            if os.path.isfile(full):
                files.append(full)
    files.sort(key=lambda x: os.path.getmtime(x))
    delete_count = len(files) // 2
    for f in files[:delete_count]:
        try:
            os.remove(f)
        except:
            pass
    print(f"已清理 {delete_count} 个旧缓存文件。")

# =============== 主命令 ===============
def jm_command(update: Update, context: CallbackContext):
    # 私聊屏蔽
    if update.effective_chat.type == "private":
        update.message.reply_text("请在群聊中使用本机器人")
        return

    if len(context.args) == 0:
        update.message.reply_text("用法：/jm <漫画ID1> <漫画ID2> ...")
        return

    load_config = jmcomic.JmOption.from_file(CONFIG_PATH)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f)
    base_path = config_data["dir_rule"]["base_dir"]

    # 自动清理缓存
    if get_folder_size(base_path) > 7 * 1024 * 1024 * 1024:
        update.message.reply_text("缓存已满，正在清理旧文件")
        delete_oldest_half(base_path)

    for album_id in context.args:
        try:
            update.message.reply_text(f"正在制作本子 {album_id} ！请稍等！")

            # 下载漫画
            jmcomic.download_album(album_id, load_config)
            album_path = os.path.join(base_path, album_id)

            # 合成 PDF（自动分卷 ≤45MB）
            pdf_files = all2PDF(album_path, base_path, album_id, max_pdf_size_mb=45)
            if isinstance(pdf_files, str):
                pdf_files = [pdf_files]

            # 发送每个分卷
            for idx, pdf_path in enumerate(pdf_files, start=1):
                try:
                    with open(pdf_path, "rb") as pdf:
                        if len(pdf_files) > 1:
                            update.message.reply_text(f"分卷 {idx}/{len(pdf_files)} 喵~")
                        update.message.reply_document(pdf)
                except Exception as e:
                    update.message.reply_text(f"发送 {pdf_path} 时出错！：{e}")

        except Exception as e:
            update.message.reply_text(f"出错了喵！：{e}")

# =============== 屏蔽私聊的所有非命令消息 ===============
def block_private(update: Update, context: CallbackContext):
    if update.effective_chat.type == "private":
        update.message.reply_text("本机器人仅限群聊使用")

# =============== 主函数入口 ===============
def main():
    try:
        updater = Updater(TOKEN, use_context=True)
        dp = updater.dispatcher

        # /jm 命令
        dp.add_handler(CommandHandler("jm", jm_command))

        # 屏蔽私聊一切消息
        dp.add_handler(MessageHandler(Filters.chat_type.private, block_private))

        updater.start_polling()
        print("✅ JMComic Bot 已启动（群聊模式）")
        updater.idle()
    except Exception as e:
        print(f"启动出错：{e}")

if __name__ == "__main__":
    main()


