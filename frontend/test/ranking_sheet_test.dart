import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/features/auth/providers.dart';
import 'package:frontend/features/rankings/presentation/ranking_sheet.dart';

class _FakeApiClient extends ApiClient {
  _FakeApiClient() : super(accessToken: () => null);

  @override
  Future<dynamic> get(String path, {Map<String, String>? query}) async => {
    'mode': 'fastest',
    'baseline_duration_seconds': 3600,
    'safety_notice': '안전 운전을 우선해 주세요.',
    'items': <dynamic>[],
  };
}

void main() {
  testWidgets('empty ranking response shows an empty state without a type error',
      (tester) async {
    await tester.pumpWidget(ProviderScope(
      overrides: [apiClientProvider.overrideWithValue(_FakeApiClient())],
      child: const MaterialApp(
        home: Scaffold(body: RankingSheet.course(courseId: 3)),
      ),
    ));

    await tester.pumpAndSettle();

    expect(find.text('아직 검증 완료된 완주자가 없습니다.'), findsOneWidget);
    expect(find.textContaining('Future<dynamic>'), findsNothing);
  });
}
