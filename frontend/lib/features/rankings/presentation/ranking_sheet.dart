import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/providers.dart';

class RankingSheet extends ConsumerWidget {
  const RankingSheet.course({required int courseId, super.key})
      : path = '/rankings/courses/$courseId';
  const RankingSheet.crewCourse({required int crewCourseId, super.key})
      : path = '/rankings/crew-courses/$crewCourseId';
  const RankingSheet.lightningCourse({required int lightningCourseId, super.key})
      : path = '/rankings/lightning-courses/$lightningCourseId';
  const RankingSheet.custom({required this.path, super.key});

  final String path;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return FutureBuilder<Map<String, dynamic>>(
      future: ref.read(apiClientProvider).getAs<Map<String, dynamic>>(path),
      builder: (context, snapshot) => Padding(
        padding: const EdgeInsets.fromLTRB(24, 0, 24, 32),
        child: snapshot.hasError
            ? Text('랭킹을 불러오지 못했습니다. ${snapshot.error}')
            : snapshot.connectionState != ConnectionState.done
                ? const SizedBox(
                    height: 160,
                    child: Center(child: CircularProgressIndicator()),
                  )
                : _RankingContent(data: snapshot.data!),
      ),
    );
  }
}

class _RankingContent extends StatelessWidget {
  const _RankingContent({required this.data});

  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final items = data['items'] as List<dynamic>? ?? [];
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('주행 랭킹', style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 8),
        Text(
          data['safety_notice']?.toString() ?? '',
          style: TextStyle(color: Theme.of(context).colorScheme.error),
        ),
        const SizedBox(height: 12),
        if (items.isEmpty)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 28),
            child: Center(child: Text('아직 검증 완료된 완주자가 없습니다.')),
          )
        else
          ...items.map((raw) {
            final item = raw as Map<String, dynamic>;
            final delta = item['baseline_delta_seconds'] as num? ?? 0;
            final baseline = data['baseline_duration_seconds'] as num?;
            final percent = baseline == null || baseline == 0
                ? null
                : delta / baseline * 100;
            final isFaster = delta < 0;
            return ListTile(
              contentPadding: EdgeInsets.zero,
              leading: CircleAvatar(child: Text('${item['rank']}')),
              title: Text(item['nickname']?.toString() ?? '사용자'),
              subtitle: Text(
                '${((item['duration_seconds'] as num) / 60).toStringAsFixed(1)}분',
              ),
              trailing: Text(
                percent == null
                    ? '${isFaster ? '' : '+'}${(delta / 60).toStringAsFixed(1)}분'
                    : '${isFaster ? '' : '+'}${percent.toStringAsFixed(1)}%',
                style: TextStyle(
                  color: isFaster ? Colors.blue : Colors.red,
                  fontWeight: FontWeight.w700,
                ),
              ),
            );
          }),
      ],
    );
  }
}
