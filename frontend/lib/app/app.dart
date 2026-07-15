import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../features/auth/application/auth_state.dart';
import '../features/auth/presentation/login_screen.dart';
import '../features/auth/providers.dart';
import 'app_shell.dart';
import 'theme/app_theme.dart';

class WayPointApp extends ConsumerWidget {
  const WayPointApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authControllerProvider);
    return MaterialApp(
      title: 'WayPoint',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      home: switch (auth.status) {
        AuthStatus.initial || AuthStatus.loading => const _LoadingScreen(),
        AuthStatus.authenticated => const AppShell(),
        AuthStatus.unauthenticated || AuthStatus.error => const LoginScreen(),
      },
    );
  }
}

class _LoadingScreen extends StatelessWidget {
  const _LoadingScreen();

  @override
  Widget build(BuildContext context) => const Scaffold(
    body: Center(child: CircularProgressIndicator()),
  );
}
