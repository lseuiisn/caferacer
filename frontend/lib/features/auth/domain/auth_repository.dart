import 'social_auth_result.dart';

abstract class AuthRepository {
  Future<AppSession> exchangeToken(SocialAuthResult socialResult);
  Future<void> logout();
  Future<AppSession?> restoreSession();
}

class AppSession {
  final String userId;
  final String accessToken;
  final String? refreshToken;
  final String? nickname;
  final String? role; // 백엔드 UserRole 값 ("USER" | "ADMIN")

  const AppSession({
    required this.userId,
    required this.accessToken,
    this.refreshToken,
    this.nickname,
    this.role,
  });

  bool get isAdmin => role?.toLowerCase() == 'admin';
}
