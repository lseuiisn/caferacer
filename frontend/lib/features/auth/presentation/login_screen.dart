import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../application/auth_state.dart';
import '../domain/social_login_type.dart';
import '../providers.dart';
import 'widgets/social_login_button.dart';

class LoginScreen extends ConsumerWidget {
  const LoginScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authControllerProvider);
    final controller = ref.read(authControllerProvider.notifier);

    ref.listen<AuthState>(authControllerProvider, (prev, next) {
      if (next.status == AuthStatus.error && next.errorMessage != null) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('로그인 실패: ${next.errorMessage}')));
      }
    });

    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Text(
                '로그인',
                style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 40),
              SocialLoginButton(
                type: SocialLoginType.kakao,
                isLoading: authState.loadingProvider == SocialLoginType.kakao,
                onPressed: () => controller.signInWith(SocialLoginType.kakao),
              ),
              const SizedBox(height: 12),
              SocialLoginButton(
                type: SocialLoginType.google,
                isLoading: authState.loadingProvider == SocialLoginType.google,
                onPressed: () => controller.signInWith(SocialLoginType.google),
              ),
              if (authState.status == AuthStatus.authenticated) ...[
                const SizedBox(height: 24),
                Text('환영합니다, ${authState.session?.nickname ?? ''}'),
                TextButton(
                  onPressed: controller.signOut,
                  child: const Text('로그아웃 (테스트용)'),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
