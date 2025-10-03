
# 初始化全局变量和数据
from .data_utils import *
ensure_data_dir()
meta = load_meta()
current_bank = meta.get("current_bank", "default")
plugin_data = load_bank(current_bank)
current_question_id: Optional[int] = plugin_data["current_question"]
def save_all():
    save_bank(current_bank, plugin_data)
    meta["current_bank"] = current_bank
    save_meta(meta)

# 注册功能模块
from .handlers_question import register_question_handlers
from .handlers_bank import register_bank_handlers
register_question_handlers(globals())
register_bank_handlers(globals())