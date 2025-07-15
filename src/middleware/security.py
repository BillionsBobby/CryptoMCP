"""安全中间件
用于FastAPI应用的安全验证和防护
"""

import time
from typing import Dict, Set
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger

from ..core.security import security_checker, security_validator


class SecurityMiddleware(BaseHTTPMiddleware):
    """安全中间件"""
    
    def __init__(self, app, max_requests_per_minute: int = 60):
        super().__init__(app)
        self.max_requests_per_minute = max_requests_per_minute
        self.rate_limiter: Dict[str, list] = {}
        
    async def dispatch(self, request: Request, call_next):
        """中间件处理逻辑"""
        start_time = time.time()
        
        # 1. 速率限制检查
        client_ip = self._get_client_ip(request)
        if not self._check_rate_limit(client_ip):
            logger.warning(f"速率限制触发: IP {client_ip}")
            return Response(
                content="Too Many Requests", 
                status_code=429,
                headers={"Retry-After": "60"}
            )
        
        # 2. 请求头安全检查
        headers = dict(request.headers)
        if not security_checker.validate_request_headers(headers):
            logger.warning(f"可疑请求头: IP {client_ip}")
            return Response(
                content="Forbidden", 
                status_code=403
            )
        
        # 3. 请求大小检查
        content_length = headers.get("content-length")
        if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB限制
            logger.warning(f"请求体过大: {content_length} bytes from {client_ip}")
            return Response(
                content="Request Entity Too Large", 
                status_code=413
            )
        
        # 4. 路径安全检查
        if self._check_suspicious_path(str(request.url.path)):
            logger.warning(f"可疑路径访问: {request.url.path} from {client_ip}")
            return Response(
                content="Forbidden", 
                status_code=403
            )
        
        # 处理请求
        try:
            response = await call_next(request)
            
            # 5. 添加安全响应头
            self._add_security_headers(response)
            
            # 记录请求时间
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            logger.error(f"请求处理异常: {str(e)}")
            return Response(
                content="Internal Server Error", 
                status_code=500
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP地址"""
        # 支持代理服务器
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def _check_rate_limit(self, client_ip: str) -> bool:
        """检查速率限制"""
        current_time = time.time()
        
        # 初始化IP记录
        if client_ip not in self.rate_limiter:
            self.rate_limiter[client_ip] = []
        
        # 清理过期记录
        requests = self.rate_limiter[client_ip]
        requests[:] = [req_time for req_time in requests if current_time - req_time < 60]
        
        # 检查是否超过限制
        if len(requests) >= self.max_requests_per_minute:
            return False
        
        # 记录当前请求
        requests.append(current_time)
        return True
    
    def _check_suspicious_path(self, path: str) -> bool:
        """检查可疑路径"""
        suspicious_patterns = [
            "/.env", "/admin", "/config", "/backup", 
            "/wp-admin", "/phpmyadmin", "/.git",
            "//", "../", "..\\", "%2e%2e",
            "<script", "javascript:", "data:",
            "union+select", "drop+table"
        ]
        
        path_lower = path.lower()
        return any(pattern in path_lower for pattern in suspicious_patterns)
    
    def _add_security_headers(self, response: Response) -> None:
        """添加安全响应头"""
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        }
        
        for header, value in security_headers.items():
            response.headers[header] = value


class SecurityAuditLogger:
    """安全审计日志记录器"""
    
    @staticmethod
    def log_security_event(event_type: str, details: Dict, severity: str = "info"):
        """记录安全事件
        
        Args:
            event_type: 事件类型
            details: 事件详情
            severity: 严重级别 (info, warning, error, critical)
        """
        log_data = {
            "event_type": event_type,
            "timestamp": time.time(),
            "severity": severity,
            "details": details
        }
        
        log_message = f"Security Event: {event_type} - {details}"
        
        if severity == "critical":
            logger.critical(log_message)
        elif severity == "error":
            logger.error(log_message)
        elif severity == "warning":
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    @staticmethod
    def log_authentication_attempt(success: bool, ip: str, user_agent: str = ""):
        """记录认证尝试"""
        SecurityAuditLogger.log_security_event(
            "authentication_attempt",
            {
                "success": success,
                "ip": ip,
                "user_agent": user_agent
            },
            "warning" if not success else "info"
        )
    
    @staticmethod
    def log_suspicious_activity(activity_type: str, ip: str, details: Dict):
        """记录可疑活动"""
        SecurityAuditLogger.log_security_event(
            "suspicious_activity",
            {
                "activity_type": activity_type,
                "ip": ip,
                **details
            },
            "warning"
        ) 