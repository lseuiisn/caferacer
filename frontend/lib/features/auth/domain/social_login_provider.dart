import 'social_auth_result.dart';

/// 실제 카카오/구글 SDK가 준비되기 전, 교체 가능한 지점(interface).
/// data/ 레이어에 Mock 구현체와, 나중에 실제 SDK 구현체를 각각 만들어서
/// providers.dart 한 곳에서만 바꿔 끼우면 된다.
abstract class SocialLoginProvider {
  Future<SocialAuthResult> signInWithKakao();
  Future<SocialAuthResult> signInWithGoogle();
  Future<void> signOut();
}
