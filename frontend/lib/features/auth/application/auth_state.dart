import '../domain/auth_repository.dart';
import '../domain/social_login_type.dart';

/// sealed class 대신 단순 status enum + payload 조합.
/// (freezed 등 코드젠 의존성 없이 바로 빌드 가능하게 하기 위함)
enum AuthStatus { initial, loading, authenticated, unauthenticated, error }

class AuthState {
  final AuthStatus status;
  final AppSession? session;
  final SocialLoginType? loadingProvider; // 어떤 버튼이 로딩 중인지 UI에서 구분용
  final String? errorMessage;

  const AuthState({
    this.status = AuthStatus.initial,
    this.session,
    this.loadingProvider,
    this.errorMessage,
  });

  AuthState copyWith({
    AuthStatus? status,
    AppSession? session,
    SocialLoginType? loadingProvider,
    String? errorMessage,
    bool clearError = false,
    bool clearLoadingProvider = false,
  }) {
    return AuthState(
      status: status ?? this.status,
      session: session ?? this.session,
      loadingProvider: clearLoadingProvider
          ? null
          : (loadingProvider ?? this.loadingProvider),
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
    );
  }
}
