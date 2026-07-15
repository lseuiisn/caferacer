import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../domain/auth_repository.dart';
import '../domain/social_login_provider.dart';
import '../domain/social_login_type.dart';
import 'auth_state.dart';

class AuthController extends StateNotifier<AuthState> {
  AuthController(this._socialLoginProvider, this._authRepository)
    : super(const AuthState()) {
    _restoreSession();
  }

  final SocialLoginProvider _socialLoginProvider;
  final AuthRepository _authRepository;
  int _operationVersion = 0;

  Future<void> _restoreSession() async {
    final operation = _operationVersion;
    final session = await _authRepository.restoreSession();
    if (operation != _operationVersion) return;
    if (session != null) {
      state = state.copyWith(
        status: AuthStatus.authenticated,
        session: session,
      );
    } else {
      state = state.copyWith(status: AuthStatus.unauthenticated);
    }
  }

  Future<void> signInWith(SocialLoginType type) async {
    final operation = ++_operationVersion;
    state = state.copyWith(
      status: AuthStatus.loading,
      loadingProvider: type,
      clearError: true,
    );
    try {
      final socialResult = type == SocialLoginType.kakao
          ? await _socialLoginProvider.signInWithKakao()
          : await _socialLoginProvider.signInWithGoogle();

      final session = await _authRepository.exchangeToken(socialResult);
      if (operation != _operationVersion) return;

      state = state.copyWith(
        status: AuthStatus.authenticated,
        session: session,
        clearLoadingProvider: true,
      );
    } catch (e) {
      if (operation != _operationVersion) return;
      state = state.copyWith(
        status: AuthStatus.error,
        errorMessage: e.toString(),
        clearLoadingProvider: true,
      );
    }
  }

  Future<void> signOut() async {
    ++_operationVersion;
    await _socialLoginProvider.signOut();
    await _authRepository.logout();
    state = const AuthState(status: AuthStatus.unauthenticated);
  }
}
