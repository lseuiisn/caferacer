import 'package:flutter/material.dart';

import '../features/cafes/presentation/cafe_list_screen.dart';
import '../features/community/presentation/community_screen.dart';
import '../features/courses/presentation/course_screen.dart';
import '../features/crews/presentation/crew_screen.dart';
import '../features/profile/presentation/profile_screen.dart';

class AppShell extends StatefulWidget {
  const AppShell({super.key});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  int _currentIndex = 0;
  static const _pages = <Widget>[
    CafeListScreen(),
    CourseScreen(),
    CommunityScreen(),
    CrewScreen(),
    ProfileScreen(),
  ];

  @override
  Widget build(BuildContext context) => Scaffold(
    body: IndexedStack(index: _currentIndex, children: _pages),
    bottomNavigationBar: NavigationBar(
      selectedIndex: _currentIndex,
      onDestinationSelected: (value) => setState(() => _currentIndex = value),
      destinations: const [
        NavigationDestination(icon: Icon(Icons.map_outlined), label: '홈'),
        NavigationDestination(icon: Icon(Icons.route_outlined), label: '코스'),
        NavigationDestination(icon: Icon(Icons.forum_outlined), label: '커뮤니티'),
        NavigationDestination(icon: Icon(Icons.groups_outlined), label: '크루'),
        NavigationDestination(icon: Icon(Icons.person_outline), label: '프로필'),
      ],
    ),
  );
}
