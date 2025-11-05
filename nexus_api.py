"""
Nexus Mods API 集成模块 - 用于检查 mod 更新
"""
import urllib.request
import urllib.error
import json
from logger import get_logger

logger = get_logger()

# Fallout 76 的 Nexus Mods 游戏域名
FALLOUT76_GAME_DOMAIN = "fallout76"


class NexusAPI:
    """Nexus Mods API 客户端"""
    
    def __init__(self, api_key):
        """
        初始化 Nexus API 客户端
        
        Args:
            api_key: Nexus Mods API Key
        """
        self.api_key = api_key
        self.base_url = "https://api.nexusmods.com/v1"
        self.headers = {
            'apikey': api_key,
            'Accept': 'application/json',
            'User-Agent': 'NexusApiClient/0.7.3 (Windows_NT 10.0.17134; x64) Node/8.9.3'
        }
    
    def _make_request(self, endpoint):
        """
        发送 API 请求
        
        Args:
            endpoint: API 端点路径（不包含 base_url）
        
        Returns:
            JSON 响应数据，失败返回 None
        """
        if not self.api_key:
            logger.warning("Nexus API Key 未配置")
            return None
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                return data
        except urllib.error.HTTPError as e:
            # 尝试读取错误响应体
            error_body = None
            try:
                error_body = e.read().decode('utf-8')
            except:
                pass
            
            if e.code == 401:
                logger.error(f"Nexus API 认证失败: 请检查 API Key 是否正确")
                if error_body:
                    logger.debug(f"错误详情: {error_body}")
            elif e.code == 404:
                logger.warning(f"Mod 不存在或无法访问: {endpoint}")
                if error_body:
                    logger.debug(f"错误详情: {error_body}")
            else:
                logger.error(f"Nexus API 请求失败: HTTP {e.code} - {url}")
                if error_body:
                    logger.error(f"错误详情: {error_body}")
            return None
        except urllib.error.URLError as e:
            logger.error(f"Nexus API 网络错误: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Nexus API 响应解析失败: {e}")
            return None
        except Exception as e:
            logger.error(f"Nexus API 请求异常: {e}")
            return None
    
    def get_mod_info(self, mod_id):
        """
        获取 Mod 基本信息
        
        Args:
            mod_id: Mod ID（字符串或整数）
        
        Returns:
            Mod 信息字典，失败返回 None
        """
        mod_id = str(mod_id)
        endpoint = f"/games/{FALLOUT76_GAME_DOMAIN}/mods/{mod_id}.json"
        return self._make_request(endpoint)
    
    def get_latest_version(self, mod_id, mod_name=None):
        """
        获取 Mod 的最新版本信息
        
        Args:
            mod_id: Mod ID（字符串或整数）
            mod_name: 可选的模组名（从 source_file 提取的第一个 '-' 前的部分），用于精确匹配文件
        
        Returns:
            最新版本信息字典，包含 version 和 upload_time 等字段，失败返回 None
        """
        mod_id = str(mod_id)
        endpoint = f"/games/{FALLOUT76_GAME_DOMAIN}/mods/{mod_id}/files.json"
        data = self._make_request(endpoint)
        
        if not data or 'files' not in data:
            return None
        
        # 获取所有文件
        files = data.get('files', [])
        if not files:
            return None
        
        matched_file = None
        
        # 如果提供了 mod_name，尝试精确匹配文件
        if mod_name:
            mod_name_lower = mod_name.lower().strip()
            matched_files = []
            
            for file_info in files:
                file_name = file_info.get('file_name', '').lower()
                name = file_info.get('name', '').lower()
                
                # 检查 file_name 或 name 是否以 mod_name 开头
                if (file_name and file_name.startswith(mod_name_lower)) or \
                   (name and name.startswith(mod_name_lower)):
                    matched_files.append(file_info)
            
            if matched_files:
                # 如果有多个匹配，选择 uploaded_time 最大的
                matched_file = max(matched_files, key=lambda f: f.get('uploaded_time', 0) or 0)
        
        # 如果找到匹配的文件
        if matched_file:
            # 提取版本号（从 version 字段或 file_name）
            version = matched_file.get('version')
            if not version:
                # 尝试从文件名提取版本号
                file_name = matched_file.get('file_name', '')
                version = self._extract_version_from_filename(file_name)
            
            file_id = matched_file.get('file_id')
            # 构造 Mod 页面链接（包含 file_id）
            mod_url = f"https://www.nexusmods.com/{FALLOUT76_GAME_DOMAIN}/mods/{mod_id}?tab=files&file_id={file_id}"
            
            return {
                'version': version,
                'upload_time': matched_file.get('uploaded_time'),
                'file_id': file_id,
                'file_name': matched_file.get('file_name'),
                'file_size': matched_file.get('file_size'),
                'mod_url': mod_url,
                'matched': True
            }
        
        # 如果找不到匹配的文件
        # 构造 Mod 页面链接（不包含 file_id）
        mod_url = f"https://www.nexusmods.com/{FALLOUT76_GAME_DOMAIN}/mods/{mod_id}?tab=files"
        
        return {
            'mod_url': mod_url,
            'matched': False,
            'match_warning': "未找到匹配的文件名"
        }
    
    def _extract_version_from_filename(self, filename):
        """
        从文件名中提取版本号
        
        Args:
            filename: 文件名
        
        Returns:
            版本号字符串，如果未找到返回 None
        """
        if not filename:
            return None
        
        # 尝试匹配常见的版本格式
        import re
        patterns = [
            r'[vV]?(\d+\.\d+\.\d+)',  # v1.2.3 或 1.2.3
            r'[vV]?(\d+\.\d+)',        # v1.2 或 1.2
            r'[vV]?(\d+)',             # v1 或 1
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                return match.group(1)
        
        return None
    
    def compare_versions(self, current_version, latest_version):
        """
        比较版本号
        
        Args:
            current_version: 当前版本号（字符串）
            latest_version: 最新版本号（字符串）
        
        Returns:
            True 如果有更新，False 如果没有更新，None 如果无法比较
        """
        if not current_version or not latest_version:
            return None
        
        # 尝试规范化版本号（去掉 'v' 前缀等）
        current = current_version.lstrip('vV').strip()
        latest = latest_version.lstrip('vV').strip()
        
        # 如果版本号相同，返回 False
        if current == latest:
            return False
        
        # 简单的字符串比较（对于标准版本号格式）
        # 这适用于 x.y.z 格式的版本号
        try:
            current_parts = [int(x) for x in current.split('.')]
            latest_parts = [int(x) for x in latest.split('.')]
            
            # 补齐长度（例如：1.2 vs 1.2.0）
            max_len = max(len(current_parts), len(latest_parts))
            current_parts.extend([0] * (max_len - len(current_parts)))
            latest_parts.extend([0] * (max_len - len(latest_parts)))
            
            # 逐位比较
            for i in range(max_len):
                if latest_parts[i] > current_parts[i]:
                    return True
                elif latest_parts[i] < current_parts[i]:
                    return False
            
            return False
        except ValueError:
            # 如果无法解析为数字，使用字符串比较
            return latest > current

