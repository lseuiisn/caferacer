import 'package:google_sign_in/google_sign_in.dart';
import 'package:kakao_flutter_sdk_user/kakao_flutter_sdk_user.dart';

import '../domain/social_auth_result.dart';
import '../domain/social_login_provider.dart';
import '../domain/social_login_type.dart';

class AppSocialLoginProvider implements SocialLoginProvider {
  AppSocialLoginProvider({required String googleServerClientId})
    : _googleSignIn = GoogleSignIn(
        serverClientId: googleServerClientId,
        scopes: const ['email'],
      );

  final GoogleSignIn _googleSignIn;

  @override
  Future<SocialAuthResult> signInWithGoogle() async {
    final account = await _googleSignIn.signIn();
    if (account == null) {
      throw Exception('구글 로그인이 취소되었습니다');
    }
    final auth = await account.authentication;
    final idToken = auth.idToken;
    if (idToken == null) {
      throw Exception('구글 ID 토큰을 받지 못했습니다 (serverClientId 설정 확인 필요)');
    }
    return SocialAuthResult(
      provider: SocialLoginType.google,
      providerToken: idToken,
      email: account.email,
      displayName: account.displayName,
      profileImageUrl: account.photoUrl,
    );
  }

  @override
  Future<SocialAuthResult> signInWithKakao() async {
    final bool kakaoTalkInstalled = await isKakaoTalkInstalled();

    OAuthToken token;
    try {
      token = kakaoTalkInstalled
          ? await UserApi.instance.loginWithKakaoTalk()
          : await UserApi.instance.loginWithKakaoAccount();
    } catch (e) {
      if (kakaoTalkInstalled) {
        token = await UserApi.instance.loginWithKakaoAccount();
      } else {
        rethrow;
      }
    }

    final user = await UserApi.instance.me();

    return SocialAuthResult(
      provider: SocialLoginType.kakao,
      providerToken: token.accessToken,
      email: user.kakaoAccount?.email,
      displayName: user.kakaoAccount?.profile?.nickname,
      profileImageUrl: user.kakaoAccount?.profile?.profileImageUrl,
    );
  }

  @override
  Future<void> signOut() async {
    await _googleSignIn.signOut();
    try {
      await UserApi.instance.logout();
    } catch (_) {}
  }
}
