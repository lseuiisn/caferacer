import '../domain/social_auth_result.dart';
import '../domain/social_login_provider.dart';
import '../domain/social_login_type.dart';

/// 카카오/구글 콘솔 키가 없어도 UI·상태 흐름을 검증할 수 있는 가짜 구현체.
/// 실제 SDK 연동 시 KakaoSocialLoginProvider, GoogleSocialLoginProvider 등으로
/// 교체하고 providers.dart의 override 한 줄만 바꾸면 된다.
class MockSocialLoginProvider implements SocialLoginProvider {
  @override
  Future<SocialAuthResult> signInWithKakao() async {
    await Future.delayed(const Duration(milliseconds: 600));
    return const SocialAuthResult(
      provider: SocialLoginType.kakao,
      providerToken: 'mock-kakao-token',
      email: 'mock.kakao@example.com',
      displayName: 'Mock Kakao User',
    );
  }

  @override
  Future<SocialAuthResult> signInWithGoogle() async {
    await Future.delayed(const Duration(milliseconds: 600));
    return const SocialAuthResult(
      provider: SocialLoginType.google,
      providerToken: 'mock-google-token',
      email: 'mock.google@example.com',
      displayName: 'Mock Google User',
    );
  }

  @override
  Future<void> signOut() async {
    await Future.delayed(const Duration(milliseconds: 200));
  }
}
