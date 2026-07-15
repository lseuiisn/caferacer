import '../domain/auth_repository.dart';
import '../domain/social_auth_result.dart';

/// 백엔드 서버 없이도 로그인 플로우 전체를 로컬에서 검증하기 위한 Mock.
/// 실제 API 붙일 때 HttpAuthRepository 등으로 교체.
class MockAuthRepository implements AuthRepository {
  AppSession? _session;

  @override
  Future<AppSession> exchangeToken(SocialAuthResult socialResult) async {
    await Future.delayed(const Duration(milliseconds: 400));
    final session = AppSession(
      userId: 'mock-uid-${socialResult.provider.name}',
      accessToken: 'mock-app-jwt',
      nickname: socialResult.displayName,
    );
    _session = session;
    return session;
  }

  @override
  Future<void> logout() async {
    await Future.delayed(const Duration(milliseconds: 200));
    _session = null;
  }

  @override
  Future<AppSession?> restoreSession() async {
    await Future.delayed(const Duration(milliseconds: 200));
    return _session;
  }
}
