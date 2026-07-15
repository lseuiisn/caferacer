import 'package:flutter/material.dart';

import '../features/cafes/presentation/cafe_finder_screen.dart';
import '../features/community/presentation/community_screen.dart';
import '../features/profile/presentation/profile_screen.dart';
import '../features/sessions/presentation/session_screen.dart';

class AppShell extends StatefulWidget {
  const AppShell({super.key});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  int _currentIndex = 0;

  @override
  Widget build(BuildContext context) => Scaffold(
    body: IndexedStack(
      index: _currentIndex,
      children: [
        CafeFinderScreen(isActive: _currentIndex == 0),
        SessionScreen(isActive: _currentIndex == 1),
        const CommunityScreen(),
        const ProfileScreen(),
      ],
    ),
    bottomNavigationBar: NavigationBar(
      selectedIndex: _currentIndex,
      onDestinationSelected: (value) => setState(() => _currentIndex = value),
      destinations: const [
        NavigationDestination(
          icon: Icon(Icons.local_cafe_outlined),
          selectedIcon: Icon(Icons.local_cafe),
          label: '카페 찾기',
        ),
        NavigationDestination(
          icon: Icon(Icons.route_outlined),
          selectedIcon: Icon(Icons.route),
          label: '세션',
        ),
        NavigationDestination(
          icon: Icon(Icons.forum_outlined),
          selectedIcon: Icon(Icons.forum),
          label: '커뮤니티',
        ),
        NavigationDestination(
          icon: Icon(Icons.person_outline),
          selectedIcon: Icon(Icons.person),
          label: '프로필',
        ),
      ],
    ),
  );
}
