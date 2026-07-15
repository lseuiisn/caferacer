// 백엔드 API 주소는 AppEnvironment의 --dart-define 설정을 사용한다.
import '../../../core/config/app_environment.dart';

class ApiConfig {
  static const String baseUrl = AppEnvironment.apiBaseUrl;
}
