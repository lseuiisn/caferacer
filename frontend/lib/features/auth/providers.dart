import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/config/app_environment.dart';
import '../../core/network/api_client.dart';
import '../../core/storage/session_store.dart';
import 'application/auth_controller.dart';
import 'application/auth_state.dart';
import 'data/app_social_login_provider.dart';
import 'data/http_auth_repository.dart';
import 'domain/auth_repository.dart';
import 'domain/social_login_provider.dart';

final socialLoginProviderProvider = Provider<SocialLoginProvider>((ref) {
  return AppSocialLoginProvider(
    googleServerClientId: AppEnvironment.googleServerClientId,
  );
});
final sessionStoreProvider = Provider<SessionStore>((ref) => SessionStore());
final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return HttpAuthRepository(ref.watch(sessionStoreProvider));
});
final authControllerProvider = StateNotifierProvider<AuthController, AuthState>(
  (ref) => AuthController(
    ref.watch(socialLoginProviderProvider),
    ref.watch(authRepositoryProvider),
  ),
);
final apiClientProvider = Provider<ApiClient>((ref) {
  final session = ref.watch(authControllerProvider).session;
  return ApiClient(accessToken: () => session?.accessToken);
});
