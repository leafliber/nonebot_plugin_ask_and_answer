from nonebot.adapters.onebot.v11 import MessageEvent, Message
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot import on_command
from .data_utils import *

list_banks_cmd = on_command("a题库列表", permission=SUPERUSER)
switch_bank_cmd = on_command("a切换题库", permission=SUPERUSER)
create_bank_cmd = on_command("a新建题库", permission=SUPERUSER)
delete_bank_cmd = on_command("a删除题库", permission=SUPERUSER)

def register_bank_handlers(globals_dict):
    @list_banks_cmd.handle()
    async def handle_list_banks(event: MessageEvent):
        banks = list_banks()
        await list_banks_cmd.send("当前题库列表：\n" + "\n".join(banks))

    @switch_bank_cmd.handle()
    async def handle_switch_bank(event: MessageEvent, msg: Message = CommandArg()):
        global current_bank, plugin_data, current_question_id
        bank_name = msg.extract_plain_text().strip()
        if not bank_name:
            await switch_bank_cmd.send("请提供题库名")
            return
        if bank_name not in list_banks():
            await switch_bank_cmd.send(f"题库 {bank_name} 不存在")
            return
        current_bank = bank_name
        plugin_data = load_bank(current_bank)
        current_question_id = plugin_data["current_question"]
        save_all()
        await switch_bank_cmd.send(f"已切换到题库：{bank_name}")

    @create_bank_cmd.handle()
    async def handle_create_bank(event: MessageEvent, msg: Message = CommandArg()):
        bank_name = msg.extract_plain_text().strip()
        if not bank_name:
            await create_bank_cmd.send("请提供新题库名")
            return
        if bank_name in list_banks():
            await create_bank_cmd.send("题库已存在")
            return
        save_bank(bank_name, {"questions": [], "current_question": None})
        await create_bank_cmd.send(f"题库 {bank_name} 创建成功！")

    @delete_bank_cmd.handle()
    async def handle_delete_bank(event: MessageEvent, msg: Message = CommandArg()):
        global current_bank, plugin_data, current_question_id
        bank_name = msg.extract_plain_text().strip()
        if not bank_name:
            await delete_bank_cmd.send("请提供要删除的题库名")
            return
        if bank_name not in list_banks():
            await delete_bank_cmd.send("题库不存在")
            return
        if bank_name == current_bank:
            await delete_bank_cmd.send("不能删除当前正在使用的题库，请先切换到其他题库")
            return
        path = get_question_bank_path(bank_name)
        os.remove(path)
        await delete_bank_cmd.send(f"题库 {bank_name} 已删除")
