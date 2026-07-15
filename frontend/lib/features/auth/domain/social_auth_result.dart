import 'social_login_type.dart';

/// 소셜 SDK 로그인 성공 시 반환되는 표준화된 결과.
/// 카카오/구글 SDK가 각각 다른 응답 형태를 주더라도
/// 이 클래스로 변환해서 상위 레이어는 SDK 종류를 몰라도 되게 한다.
class SocialAuthResult {
  final SocialLoginType provider;
  final String providerToken; // SDK가 준 access token (백엔드 검증용)
  final String? email;
  final String? displayName;
  final String? profileImageUrl;

  const SocialAuthResult({
    required this.provider,
    required this.providerToken,
    this.email,
    this.displayName,
    this.profileImageUrl,
  });
}
