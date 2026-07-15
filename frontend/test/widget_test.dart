import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/app/app_shell.dart';

void main() {
  testWidgets('five main navigation tabs are visible', (tester) async {
    await tester.pumpWidget(
      const ProviderScope(child: MaterialApp(home: AppShell())),
    );

    expect(find.text('홈'), findsOneWidget);
    expect(find.text('코스'), findsOneWidget);
    expect(find.text('커뮤니티'), findsOneWidget);
    expect(find.text('크루'), findsOneWidget);
    expect(find.text('프로필'), findsOneWidget);
  });
}
