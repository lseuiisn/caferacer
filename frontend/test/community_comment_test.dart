import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/features/auth/providers.dart';
import 'package:frontend/features/community/presentation/community_screen.dart';

class _CommunityApiClient extends ApiClient {
  _CommunityApiClient() : super(accessToken: () => null);

  @override
  Future<dynamic> get(String path, {Map<String, String>? query}) async {
    if (path == '/posts') {
      return {
        'items': [
          {
            'id': 1,
            'author_id': 2,
            'author_nickname': '작성자',
            'content': '테스트 게시글',
            'image_urls': <String>[],
            'like_count': 0,
            'comment_count': 0,
            'liked_by_me': false,
          },
        ],
      };
    }
    if (path == '/posts/1/comments') return <dynamic>[];
    throw StateError('Unexpected GET $path');
  }

  @override
  Future<dynamic> post(String path, {Object? body}) async => <String, dynamic>{};
}

void main() {
  testWidgets('submitting a comment keeps the bottom sheet widget tree valid',
      (tester) async {
    await tester.pumpWidget(ProviderScope(
      overrides: [apiClientProvider.overrideWithValue(_CommunityApiClient())],
      child: const MaterialApp(home: CommunityScreen()),
    ));
    await tester.pumpAndSettle();

    await tester.tap(find.textContaining('댓글'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), '새 댓글');
    await tester.tap(find.byIcon(Icons.send));
    await tester.pumpAndSettle();

    expect(find.text('첫 댓글을 남겨보세요.'), findsOneWidget);
    expect(tester.takeException(), isNull);

    Navigator.of(tester.element(find.text('첫 댓글을 남겨보세요.'))).pop();
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });
}
