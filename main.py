from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
import requests
from datetime import datetime


@register(
    name="eve_tools",
    version="v1.1",
    author="Persona", 
    desc="EVE角色信息查询工具"
)
import requests
from datetime import datetime


@register(
    name="eve_tools",
    version="v1.0",
    author="Persona", 
    desc="EVE角色信息查询工具"
)
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
    
    @filter.command("eveid")
    async def handle_eveid(self, event: AstrMessageEvent):
        """处理eveid查询请求"""
        try:
            # 从消息内容提取角色名称（格式：/eveid 角色名）
            character_name = event.message_str.split(maxsplit=1)[1]
            result = eveid(character_name)
            yield event.plain_result(result)
        except Exception as e:
            logger.error(f"查询失败: {str(e)}")
            yield event.plain_result(f"角色信息查询失败: {str(e)}")


# 配置API访问
access_token = "your_access_token"
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

def get_character_id(name):
    """获取角色ID"""
    try:
        response = requests.post(
            "https://ali-esi.evepc.163.com/latest/universe/ids/",
            headers=headers,
            json=[name]
        )
        response.raise_for_status()
        data = response.json()
        
        for char in data.get('characters', []):
            if char['name'].lower() == name.lower():
                return char['id']
        return None
    except requests.exceptions.RequestException as e:
        print(f"获取角色ID失败: {e}")
        return None

def get_corp_history(character_id):
    """获取军团历史记录"""
    try:
        response = requests.get(
            f"https://ali-esi.evepc.163.com/latest/characters/{character_id}/corporationhistory/",
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"获取雇佣记录失败: {e}")
        return None

def get_corp_details(corp_id, record, character_id):
    """获取军团详细信息"""
    try:
        response = requests.get(
            f"https://ali-esi.evepc.163.com/latest/corporations/{corp_id}",
            headers=headers
        )
        response.raise_for_status()
        corp_data = response.json()
        
        alliance_name = '无联盟'
        if corp_data.get('alliance_id'):
            try:
                alliance_response = requests.get(
                    f"https://ali-esi.evepc.163.com/latest/alliances/{corp_data['alliance_id']}/",
                    headers=headers
                )
                alliance_response.raise_for_status()
                alliance_name = alliance_response.json().get('name', '无联盟')
            except requests.exceptions.RequestException:
                pass
        
        return {
            'name': f"{corp_data['name']} [{alliance_name}]",
            'start_date': record['start_date'].replace('T', ' ').replace('Z', ''),
            'character_id': character_id,
            'corp_id': record['corporation_id']  # 添加军团ID
        }
    except requests.exceptions.RequestException as e:
        print(f"获取军团信息失败: {e}")
        return None

def eveid(name: str) -> str:
    """查询角色雇佣记录
    Args:
        name: EVE角色名称
    Returns:
        格式化后的雇佣记录字符串
    """
    character_id = get_character_id(name)
    if not character_id:
        return f"未找到角色: {name}"
        
    # 获取军团历史记录
    corp_history = get_corp_history(character_id)
    if not corp_history:
        return "没有找到军团雇佣记录"
        
    # 处理每个军团记录
    corporations = []
    for record in corp_history:
        corp_details = get_corp_details(record['corporation_id'], record, character_id)
        if corp_details:
            corporations.append(corp_details)
    
    # 计算持续时间
    current_time = datetime.now()
    for i in range(len(corporations)):
        start = datetime.strptime(corporations[i]['start_date'], "%Y-%m-%d %H:%M:%S")
        end = current_time if i == 0 else datetime.strptime(corporations[i-1]['start_date'], "%Y-%m-%d %H:%M:%S")
        duration = (end - start).days
        if duration == 0:  # 处理0天的情况
            duration = 1
        duration_str = f"{duration}天" if i > 0 else f"至今 {duration}天"
        corporations[i]['duration'] = duration_str
    
    # 构造结果
    result = {
        'status': 'success',
        'data': {
            'character_name': name,
            'character_id': character_id,
            'corp_history': corporations
        }
    }
    
    # 格式化输出文本
    output = f"角色 {name} (角色ID: {character_id}) 的雇佣历史：\n"
    for corp in result['data']['corp_history']:
        output += f"[{corp['start_date']}] 加入 {corp['name']} (ID: {corp['corp_id']})\n"
        output += f"└─ 雇佣时长: {corp['duration']}\n\n"
    
    return output

# 保留测试入口
if __name__ == "__main__":
    name = input("请输入角色名称: ")
    print(eveid(name))