import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';

import '../../../app/theme/app_theme.dart';
import '../../../shared/widgets/tmap_native_map.dart';
import '../../auth/providers.dart';
import '../../courses/presentation/lightning_course_form.dart';
import '../../crews/presentation/crew_screen.dart';
import '../../drive_tracking/presentation/drive_session_screen.dart';
import '../../navigation/domain/navigation_gateway.dart';
import '../../rankings/presentation/ranking_sheet.dart';

final dailySessionsProvider =
    FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) async {
      final api = ref.watch(apiClientProvider);
      final response = await api.get('/daily-courses') as Map<String, dynamic>;
      final items = response['items'] as List<dynamic>? ?? const [];
      return Future.wait(
        items.map((raw) async {
          final item = raw as Map<String, dynamic>;
          final course = item['course'] as Map<String, dynamic>;
          return await api.get('/courses/${course['id']}')
              as Map<String, dynamic>;
        }),
      );
    });

final publicSessionsProvider =
    FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) async {
      final response =
          await ref.watch(apiClientProvider).get('/lightning-courses')
              as Map<String, dynamic>;
      return (response['items'] as List<dynamic>? ?? const [])
          .cast<Map<String, dynamic>>();
    });

final crewSessionsProvider =
    FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) async {
      final api = ref.watch(apiClientProvider);
      final response = await api.get('/crews') as Map<String, dynamic>;
      final crews = (response['items'] as List<dynamic>? ?? const [])
          .cast<Map<String, dynamic>>()
          .where((crew) => crew['my_status'] == 'active');
      final groups = await Future.wait(
        crews.map((crew) async {
          final courses =
              await api.get('/crews/${crew['id']}/courses') as List<dynamic>;
          return courses.cast<Map<String, dynamic>>().map((course) {
            return <String, dynamic>{...course, 'crew_name': crew['name']};
          }).toList();
        }),
      );
      return groups.expand((items) => items).toList();
    });

enum _SessionKind { daily, public, crew }

class SessionScreen extends ConsumerStatefulWidget {
  const SessionScreen({this.isActive = true, super.key});

  final bool isActive;

  @override
  ConsumerState<SessionScreen> createState() => _SessionScreenState();
}

class _SessionScreenState extends ConsumerState<SessionScreen> {
  final Set<_SessionKind> _visibleKinds = _SessionKind.values.toSet();

  @override
  Widget build(BuildContext context) {
    final daily = ref.watch(dailySessionsProvider);
    final publicSessions = ref.watch(publicSessionsProvider);
    final crew = ref.watch(crewSessionsProvider);
    final entries = <_SessionEntry>[
      if (_visibleKinds.contains(_SessionKind.daily))
        ...(daily.valueOrNull ?? const []).map(_SessionEntry.daily),
      if (_visibleKinds.contains(_SessionKind.public))
        ...(publicSessions.valueOrNull ?? const []).map(_SessionEntry.public),
      if (_visibleKinds.contains(_SessionKind.crew))
        ...(crew.valueOrNull ?? const []).map(_SessionEntry.crew),
    ];
    final isLoading =
        (_visibleKinds.contains(_SessionKind.daily) && daily.isLoading) ||
        (_visibleKinds.contains(_SessionKind.public) &&
            publicSessions.isLoading) ||
        (_visibleKinds.contains(_SessionKind.crew) && crew.isLoading);
    final error = daily.error ?? publicSessions.error ?? crew.error;

    return Scaffold(
      body: Stack(
        children: [
          Positioned.fill(
            child: error != null
                ? _SessionMessage(
                    icon: Icons.cloud_off_outlined,
                    message: '세션을 불러오지 못했습니다.\n$error',
                  )
                : isLoading && entries.isEmpty
                ? const Center(child: CircularProgressIndicator())
                : _SessionMap(entries: entries, isActive: widget.isActive),
          ),
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: SafeArea(
              bottom: false,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                child: _SessionHeader(
                  visibleKinds: _visibleKinds,
                  onToggle: (kind, selected) => setState(() {
                    selected
                        ? _visibleKinds.add(kind)
                        : _visibleKinds.remove(kind);
                  }),
                  onRefresh: _refresh,
                  onCreate: _createPublicSession,
                  onOpenCrews: _openCrewHub,
                ),
              ),
            ),
          ),
          if (!isLoading && entries.isEmpty && error == null)
            const Positioned(
              left: 16,
              right: 16,
              bottom: 16,
              child: _EmptySessionCard(),
            ),
          if (entries.isNotEmpty)
            Positioned(
              left: 0,
              right: 0,
              bottom: 14,
              height: 130,
              child: ListView.separated(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                scrollDirection: Axis.horizontal,
                itemCount: entries.length,
                separatorBuilder: (_, _) => const SizedBox(width: 10),
                itemBuilder: (context, index) => _SessionPreviewCard(
                  entry: entries[index],
                  onTap: () => _showSession(entries[index]),
                ),
              ),
            ),
        ],
      ),
    );
  }

  void _refresh() {
    ref.invalidate(dailySessionsProvider);
    ref.invalidate(publicSessionsProvider);
    ref.invalidate(crewSessionsProvider);
  }

  Future<void> _createPublicSession() async {
    final created = await Navigator.push<bool>(
      context,
      MaterialPageRoute(builder: (_) => const LightningCourseForm()),
    );
    if (created == true) ref.invalidate(publicSessionsProvider);
  }

  Future<void> _openCrewHub() async {
    await Navigator.push<void>(
      context,
      MaterialPageRoute(builder: (_) => const CrewScreen()),
    );
    ref.invalidate(crewSessionsProvider);
  }

  void _showSession(_SessionEntry entry) {
    switch (entry.kind) {
      case _SessionKind.daily:
        _showDailySession(entry.data);
      case _SessionKind.public:
        _showPublicSession(entry.data);
      case _SessionKind.crew:
        _showCrewSession(entry.data);
    }
  }

  void _showDailySession(Map<String, dynamic> course) {
    final anchors = (course['navigation_anchors'] as List<dynamic>? ?? const [])
        .cast<Map<String, dynamic>>();
    final start = anchors
        .where((anchor) => anchor['anchor_type'] == 'start')
        .firstOrNull;
    final path = _dailyPath(course);
    final startPoint =
        start ??
        (path.isEmpty
            ? null
            : <String, dynamic>{
                'name': '코스 시작점',
                'latitude': path.first.latitude,
                'longitude': path.first.longitude,
              });
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (sheetContext) => _SessionDetailSheet(
        badge: 'TODAY COURSE',
        badgeColor: AppColors.lime,
        title: course['name'].toString(),
        description:
            course['description']?.toString() ?? course['region'].toString(),
        facts: [
          '${_distanceLabel(course['estimated_distance_meters'])} 거리',
          '${course['estimated_duration_minutes']}분 예상',
          '${course['difficulty']} 난이도',
        ],
        secondaryLabel: '랭킹 보기',
        onSecondary: () => showModalBottomSheet<void>(
          context: context,
          builder: (_) => RankingSheet.course(courseId: course['id'] as int),
        ),
        primaryLabel: '주행 시작',
        onPrimary: startPoint == null
            ? null
            : () {
                Navigator.pop(sheetContext);
                startDriveFlow(
                  context,
                  ref,
                  DriveTarget(
                    name: course['name'].toString(),
                    courseId: course['id'] as int,
                    start: NavigationPoint(
                      name: startPoint['name']?.toString() ?? '코스 시작점',
                      latitude: (startPoint['latitude'] as num).toDouble(),
                      longitude: (startPoint['longitude'] as num).toDouble(),
                    ),
                  ),
                );
              },
      ),
    );
  }

  void _showPublicSession(Map<String, dynamic> session) {
    var joined = session['joined_by_me'] == true;
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (sheetContext) => StatefulBuilder(
        builder: (context, setSheetState) => _SessionDetailSheet(
          badge: 'OPEN SESSION',
          badgeColor: AppColors.ink,
          badgeForeground: Colors.white,
          title: session['name'].toString(),
          description:
              '${session['start_name']} → ${session['destination_name']}',
          facts: [
            '${session['event_date']}',
            '${session['participant_count']}명 참여',
            _rankingLabel(session['ranking_mode']),
          ],
          secondaryLabel: joined ? '랭킹 보기' : null,
          onSecondary: joined
              ? () => showModalBottomSheet<void>(
                  context: context,
                  builder: (_) => RankingSheet.lightningCourse(
                    lightningCourseId: session['id'] as int,
                  ),
                )
              : null,
          primaryLabel: joined ? '주행 시작' : '세션 참여',
          onPrimary: () async {
            if (!joined) {
              await ref
                  .read(apiClientProvider)
                  .post('/lightning-courses/${session['id']}/join');
              session['joined_by_me'] = true;
              setSheetState(() => joined = true);
              ref.invalidate(publicSessionsProvider);
              return;
            }
            final start = session['start'] as Map<String, dynamic>;
            if (!sheetContext.mounted) return;
            Navigator.pop(sheetContext);
            startDriveFlow(
              context,
              ref,
              DriveTarget(
                name: session['name'].toString(),
                lightningCourseId: session['id'] as int,
                start: NavigationPoint(
                  name: session['start_name'].toString(),
                  latitude: (start['latitude'] as num).toDouble(),
                  longitude: (start['longitude'] as num).toDouble(),
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  void _showCrewSession(Map<String, dynamic> session) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (sheetContext) => _SessionDetailSheet(
        badge: session['crew_name']?.toString() ?? 'CREW SESSION',
        badgeColor: AppColors.blue,
        badgeForeground: Colors.white,
        title: session['name'].toString(),
        description:
            '${session['start_name']} → ${session['destination_name']}',
        facts: [
          '${session['event_date']}',
          _rankingLabel(session['ranking_mode']),
          '크루 전용',
        ],
        secondaryLabel: '랭킹 보기',
        onSecondary: () => showModalBottomSheet<void>(
          context: context,
          builder: (_) =>
              RankingSheet.crewCourse(crewCourseId: session['id'] as int),
        ),
        primaryLabel: '주행 시작',
        onPrimary: () {
          final start = session['start'] as Map<String, dynamic>;
          Navigator.pop(sheetContext);
          startDriveFlow(
            context,
            ref,
            DriveTarget(
              name: session['name'].toString(),
              crewCourseId: session['id'] as int,
              start: NavigationPoint(
                name: session['start_name'].toString(),
                latitude: (start['latitude'] as num).toDouble(),
                longitude: (start['longitude'] as num).toDouble(),
              ),
            ),
          );
        },
      ),
    );
  }
}

class _SessionHeader extends StatelessWidget {
  const _SessionHeader({
    required this.visibleKinds,
    required this.onToggle,
    required this.onRefresh,
    required this.onCreate,
    required this.onOpenCrews,
  });

  final Set<_SessionKind> visibleKinds;
  final void Function(_SessionKind kind, bool selected) onToggle;
  final VoidCallback onRefresh;
  final VoidCallback onCreate;
  final VoidCallback onOpenCrews;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.fromLTRB(18, 16, 14, 14),
    decoration: BoxDecoration(
      color: AppColors.surface.withValues(alpha: 0.96),
      borderRadius: BorderRadius.circular(24),
      border: Border.all(color: AppColors.ink, width: 1.2),
      boxShadow: const [
        BoxShadow(
          color: Color(0x22000000),
          blurRadius: 18,
          offset: Offset(0, 7),
        ),
      ],
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'WAYPOINT',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 1.8,
                    ),
                  ),
                  Text(
                    'LIVE SESSIONS',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                ],
              ),
            ),
            _RoundAction(
              tooltip: '새로고침',
              icon: Icons.refresh,
              onPressed: onRefresh,
            ),
            const SizedBox(width: 8),
            _RoundAction(
              tooltip: '크루 관리',
              icon: Icons.groups_outlined,
              onPressed: onOpenCrews,
            ),
            const SizedBox(width: 8),
            _RoundAction(
              tooltip: '공개 세션 만들기',
              icon: Icons.add,
              foreground: AppColors.ink,
              background: AppColors.lime,
              onPressed: onCreate,
            ),
          ],
        ),
        const SizedBox(height: 12),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            children: [
              _kindChip(_SessionKind.daily, '오늘의 코스'),
              const SizedBox(width: 8),
              _kindChip(_SessionKind.public, '공개 번개'),
              const SizedBox(width: 8),
              _kindChip(_SessionKind.crew, '내 크루'),
            ],
          ),
        ),
      ],
    ),
  );

  Widget _kindChip(_SessionKind kind, String label) => FilterChip(
    label: Text(label),
    selected: visibleKinds.contains(kind),
    onSelected: (selected) => onToggle(kind, selected),
  );
}

class _RoundAction extends StatelessWidget {
  const _RoundAction({
    required this.tooltip,
    required this.icon,
    required this.onPressed,
    this.foreground = Colors.white,
    this.background = AppColors.ink,
  });

  final String tooltip;
  final IconData icon;
  final VoidCallback onPressed;
  final Color foreground;
  final Color background;

  @override
  Widget build(BuildContext context) => IconButton(
    tooltip: tooltip,
    onPressed: onPressed,
    color: foreground,
    style: IconButton.styleFrom(
      backgroundColor: background,
      fixedSize: const Size(42, 42),
    ),
    icon: Icon(icon, size: 21),
  );
}

class _SessionMap extends StatelessWidget {
  const _SessionMap({required this.entries, required this.isActive});

  final List<_SessionEntry> entries;
  final bool isActive;

  @override
  Widget build(BuildContext context) {
    final center = entries.isEmpty || entries.first.path.isEmpty
        ? const LatLng(37.5665, 126.9780)
        : entries.first.path.first;
    if (Platform.isAndroid) {
      if (!isActive) return const SizedBox.shrink();
      return TmapNativeMap(
        centerLatitude: center.latitude,
        centerLongitude: center.longitude,
        zoom: 10,
        markers: const [],
        polylines: entries
            .where((entry) => entry.path.length >= 2)
            .map(
              (entry) => TmapNativePolyline(
                id: '${entry.kind.name}:${entry.data['id']}',
                points: entry.path
                    .map((point) => [point.latitude, point.longitude])
                    .toList(),
                color: entry.hexColor,
                width: entry.kind == _SessionKind.daily ? 9 : 7,
              ),
            )
            .toList(),
      );
    }
    return FlutterMap(
      options: MapOptions(initialCenter: center, initialZoom: 10),
      children: [
        TileLayer(
          urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
          userAgentPackageName: 'com.waypoint.app',
        ),
        PolylineLayer(
          polylines: entries
              .where((entry) => entry.path.length >= 2)
              .map(
                (entry) => Polyline(
                  points: entry.path,
                  color: entry.color,
                  strokeWidth: entry.kind == _SessionKind.daily ? 6 : 5,
                ),
              )
              .toList(),
        ),
        const RichAttributionWidget(
          attributions: [TextSourceAttribution('OpenStreetMap contributors')],
        ),
      ],
    );
  }
}

class _SessionEntry {
  const _SessionEntry({
    required this.kind,
    required this.data,
    required this.path,
    required this.title,
    required this.subtitle,
    required this.badge,
    required this.color,
    required this.hexColor,
  });

  factory _SessionEntry.daily(Map<String, dynamic> course) => _SessionEntry(
    kind: _SessionKind.daily,
    data: course,
    path: _dailyPath(course),
    title: course['name'].toString(),
    subtitle:
        '${course['estimated_duration_minutes']}분 · ${_distanceLabel(course['estimated_distance_meters'])}',
    badge: 'TODAY',
    color: AppColors.ink,
    hexColor: '#111111',
  );

  factory _SessionEntry.public(Map<String, dynamic> session) => _SessionEntry(
    kind: _SessionKind.public,
    data: session,
    path: _straightPath(session),
    title: session['name'].toString(),
    subtitle: '${session['start_name']} → ${session['destination_name']}',
    badge: 'OPEN',
    color: AppColors.lime,
    hexColor: '#C8FF00',
  );

  factory _SessionEntry.crew(Map<String, dynamic> session) => _SessionEntry(
    kind: _SessionKind.crew,
    data: session,
    path: _straightPath(session),
    title: session['name'].toString(),
    subtitle: '${session['start_name']} → ${session['destination_name']}',
    badge: session['crew_name']?.toString() ?? 'CREW',
    color: AppColors.blue,
    hexColor: '#3274F6',
  );

  final _SessionKind kind;
  final Map<String, dynamic> data;
  final List<LatLng> path;
  final String title;
  final String subtitle;
  final String badge;
  final Color color;
  final String hexColor;
}

class _SessionPreviewCard extends StatelessWidget {
  const _SessionPreviewCard({required this.entry, required this.onTap});

  final _SessionEntry entry;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => SizedBox(
    width: 285,
    child: Material(
      color: AppColors.surface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(22),
        side: const BorderSide(color: AppColors.ink, width: 1.2),
      ),
      elevation: 5,
      shadowColor: Colors.black26,
      child: InkWell(
        borderRadius: BorderRadius.circular(22),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Container(
                width: 8,
                height: double.infinity,
                decoration: BoxDecoration(
                  color: entry.color,
                  borderRadius: BorderRadius.circular(99),
                  border: entry.color == AppColors.lime
                      ? Border.all(color: AppColors.ink)
                      : null,
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      entry.badge.toUpperCase(),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 1.2,
                      ),
                    ),
                    const SizedBox(height: 5),
                    Text(
                      entry.title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      entry.subtitle,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: AppColors.mutedInk,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.arrow_forward, size: 20),
            ],
          ),
        ),
      ),
    ),
  );
}

class _SessionDetailSheet extends StatelessWidget {
  const _SessionDetailSheet({
    required this.badge,
    required this.badgeColor,
    required this.title,
    required this.description,
    required this.facts,
    required this.primaryLabel,
    required this.onPrimary,
    this.badgeForeground = AppColors.ink,
    this.secondaryLabel,
    this.onSecondary,
  });

  final String badge;
  final Color badgeColor;
  final Color badgeForeground;
  final String title;
  final String description;
  final List<String> facts;
  final String primaryLabel;
  final VoidCallback? onPrimary;
  final String? secondaryLabel;
  final VoidCallback? onSecondary;

  @override
  Widget build(BuildContext context) => SafeArea(
    child: Padding(
      padding: const EdgeInsets.fromLTRB(24, 4, 24, 24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
            decoration: BoxDecoration(
              color: badgeColor,
              borderRadius: BorderRadius.circular(999),
              border: Border.all(color: AppColors.ink),
            ),
            child: Text(
              badge.toUpperCase(),
              style: TextStyle(
                color: badgeForeground,
                fontSize: 10,
                fontWeight: FontWeight.w900,
                letterSpacing: 1.1,
              ),
            ),
          ),
          const SizedBox(height: 14),
          Text(title, style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 8),
          Text(description, style: const TextStyle(color: AppColors.mutedInk)),
          const SizedBox(height: 16),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: facts.map((fact) => Chip(label: Text(fact))).toList(),
          ),
          const SizedBox(height: 22),
          Row(
            children: [
              if (secondaryLabel != null && onSecondary != null) ...[
                Expanded(
                  child: OutlinedButton(
                    onPressed: onSecondary,
                    child: Text(secondaryLabel!),
                  ),
                ),
                const SizedBox(width: 10),
              ],
              Expanded(
                child: FilledButton(
                  onPressed: onPrimary,
                  style: FilledButton.styleFrom(
                    backgroundColor: AppColors.lime,
                    foregroundColor: AppColors.ink,
                    side: const BorderSide(color: AppColors.ink),
                  ),
                  child: Text(primaryLabel),
                ),
              ),
            ],
          ),
        ],
      ),
    ),
  );
}

class _SessionMessage extends StatelessWidget {
  const _SessionMessage({required this.icon, required this.message});

  final IconData icon;
  final String message;

  @override
  Widget build(BuildContext context) => ColoredBox(
    color: AppColors.canvas,
    child: Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 42),
            const SizedBox(height: 12),
            Text(message, textAlign: TextAlign.center),
          ],
        ),
      ),
    ),
  );
}

class _EmptySessionCard extends StatelessWidget {
  const _EmptySessionCard();

  @override
  Widget build(BuildContext context) => Material(
    color: AppColors.surface,
    elevation: 6,
    shadowColor: Colors.black26,
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(22),
      side: const BorderSide(color: AppColors.ink, width: 1.2),
    ),
    child: const Padding(
      padding: EdgeInsets.symmetric(horizontal: 18, vertical: 17),
      child: Row(
        children: [
          DecoratedBox(
            decoration: BoxDecoration(
              color: AppColors.lime,
              shape: BoxShape.circle,
            ),
            child: Padding(
              padding: EdgeInsets.all(10),
              child: Icon(Icons.route_outlined, size: 22),
            ),
          ),
          SizedBox(width: 14),
          Expanded(
            child: Text(
              '선택한 조건의 세션이 없습니다.',
              style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800),
            ),
          ),
        ],
      ),
    ),
  );
}

List<LatLng> _dailyPath(Map<String, dynamic> course) {
  final path = course['path'];
  if (path is! Map<String, dynamic>) return const [];
  final coordinates = path['coordinates'];
  if (coordinates is! List<dynamic>) return const [];
  return coordinates
      .whereType<List<dynamic>>()
      .where((pair) => pair.length >= 2)
      .map(
        (pair) =>
            LatLng((pair[0] as num).toDouble(), (pair[1] as num).toDouble()),
      )
      .toList();
}

List<LatLng> _straightPath(Map<String, dynamic> session) {
  final start = session['start'];
  final destination = session['destination'];
  if (start is! Map<String, dynamic> || destination is! Map<String, dynamic>) {
    return const [];
  }
  return [
    LatLng(
      (start['latitude'] as num).toDouble(),
      (start['longitude'] as num).toDouble(),
    ),
    LatLng(
      (destination['latitude'] as num).toDouble(),
      (destination['longitude'] as num).toDouble(),
    ),
  ];
}

String _distanceLabel(dynamic rawMeters) {
  final meters = rawMeters is num ? rawMeters.toDouble() : 0;
  return meters >= 1000
      ? '${(meters / 1000).toStringAsFixed(1)}km'
      : '${meters.round()}m';
}

String _rankingLabel(dynamic mode) =>
    mode == 'closest_to_baseline' ? '기준 시간 근접순' : '완주 시간순';
