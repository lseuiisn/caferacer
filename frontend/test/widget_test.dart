import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/app/app_shell.dart';

void main() {
  testWidgets('four main navigation tabs are visible', (tester) async {
    await tester.pumpWidget(
      const ProviderScope(child: MaterialApp(home: AppShell())),
    );

    final navigation = find.byType(NavigationBar);
    expect(
      find.descendant(of: navigation, matching: find.text('카페 찾기')),
      findsOneWidget,
    );
    expect(
      find.descendant(of: navigation, matching: find.text('세션')),
      findsOneWidget,
    );
    expect(
      find.descendant(of: navigation, matching: find.text('커뮤니티')),
      findsOneWidget,
    );
    expect(
      find.descendant(of: navigation, matching: find.text('프로필')),
      findsOneWidget,
    );
    expect(find.text('코스'), findsNothing);
    expect(find.text('크루'), findsNothing);
  });
}
