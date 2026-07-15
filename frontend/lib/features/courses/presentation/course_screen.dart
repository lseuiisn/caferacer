import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';

import '../../../shared/widgets/tmap_native_map.dart';
import '../../auth/providers.dart';
import '../../drive_tracking/presentation/drive_session_screen.dart';
import '../../navigation/domain/navigation_gateway.dart';
import '../../rankings/presentation/ranking_sheet.dart';
import 'lightning_course_form.dart';

final dailyCoursesProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) async {
  final daily = await ref.watch(apiClientProvider).get('/daily-courses') as Map<String, dynamic>;
  final items = daily['items'] as List<dynamic>? ?? [];
  return Future.wait(items.map((item) async {
    final course = (item as Map<String, dynamic>)['course'] as Map<String, dynamic>;
    return await ref.watch(apiClientProvider).get('/courses/${course['id']}')
        as Map<String, dynamic>;
  }));
});

final lightningCoursesProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) async {
  final page = await ref.watch(apiClientProvider).get('/lightning-courses')
      as Map<String, dynamic>;
  return (page['items'] as List<dynamic>? ?? []).cast<Map<String, dynamic>>();
});

class CourseScreen extends ConsumerStatefulWidget {
  const CourseScreen({super.key});

  @override
  ConsumerState<CourseScreen> createState() => _CourseScreenState();
}

class _CourseScreenState extends ConsumerState<CourseScreen> {
  bool _showToday = true;
  bool _showLightning = true;

  @override
  Widget build(BuildContext context) {
    final daily = ref.watch(dailyCoursesProvider);
    final lightning = ref.watch(lightningCoursesProvider);
    final loading = (_showToday && daily.isLoading) || (_showLightning && lightning.isLoading);
    final error = (_showToday ? daily.error : null) ??
        (_showLightning ? lightning.error : null);
    final courses = _showToday ? (daily.valueOrNull ?? <Map<String, dynamic>>[]) : <Map<String, dynamic>>[];
    final lightningItems = _showLightning
        ? (lightning.valueOrNull ?? <Map<String, dynamic>>[])
        : <Map<String, dynamic>>[];

    return Scaffold(
      appBar: AppBar(
        title: const Text('코스'),
        actions: [
          IconButton(
            tooltip: '새로고침',
            onPressed: () {
              ref.invalidate(dailyCoursesProvider);
              ref.invalidate(lightningCoursesProvider);
            },
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () async {
          final created = await Navigator.push<bool>(context, MaterialPageRoute(
            builder: (_) => const LightningCourseForm(),
          ));
          if (created == true) ref.invalidate(lightningCoursesProvider);
        },
        icon: const Icon(Icons.bolt),
        label: const Text('번개 만들기'),
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
            child: Row(children: [
              FilterChip(
                label: const Text('오늘의 코스'),
                selected: _showToday,
                onSelected: (value) => setState(() => _showToday = value),
              ),
              const SizedBox(width: 8),
              FilterChip(
                label: const Text('공개 번개코스'),
                selected: _showLightning,
                onSelected: (value) => setState(() => _showLightning = value),
              ),
            ]),
          ),
          Expanded(
            child: loading
                ? const Center(child: CircularProgressIndicator())
                : error != null
                    ? Center(child: Text('$error'))
                    : _CourseMap(
                        courses: courses,
                        lightningCourses: lightningItems,
                        onCourseTap: _showCourseDetail,
                        onLightningTap: _showLightningDetail,
                      ),
          ),
        ],
      ),
    );
  }

  void _showCourseDetail(Map<String, dynamic> course) {
    final anchors = (course['navigation_anchors'] as List<dynamic>? ?? [])
        .cast<Map<String, dynamic>>();
    final start = anchors.where((item) => item['anchor_type'] == 'start').firstOrNull;
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (sheetContext) => Padding(
        padding: const EdgeInsets.fromLTRB(24, 0, 24, 32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(course['name'].toString(), style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            Text(course['description']?.toString() ?? course['region'].toString()),
            const SizedBox(height: 8),
            Text('${((course['estimated_distance_meters'] as num) / 1000).toStringAsFixed(1)}km · '
                '${course['estimated_duration_minutes']}분 · ${course['difficulty']}'),
            Text('추천 카페 ${(course['cafes'] as List<dynamic>? ?? []).length}곳 · '
                '경유지 최대 10개'),
            const SizedBox(height: 16),
            Row(children: [
              Expanded(child: OutlinedButton.icon(
                onPressed: () => showModalBottomSheet<void>(
                  context: context,
                  showDragHandle: true,
                  builder: (_) => RankingSheet.course(courseId: course['id'] as int),
                ),
                icon: const Icon(Icons.emoji_events_outlined),
                label: const Text('랭킹 보기'),
              )),
              const SizedBox(width: 8),
              Expanded(child: FilledButton.icon(
                onPressed: start == null ? null : () {
                  Navigator.pop(sheetContext);
                  startDriveFlow(context, ref, DriveTarget(
                    name: course['name'].toString(),
                    courseId: course['id'] as int,
                    start: NavigationPoint(
                      name: start['name']?.toString() ?? '코스 시작점',
                      latitude: (start['latitude'] as num).toDouble(),
                      longitude: (start['longitude'] as num).toDouble(),
                    ),
                  ));
                },
                icon: const Icon(Icons.navigation),
                label: const Text('주행 시작'),
              )),
            ]),
          ],
        ),
      ),
    );
  }

  void _showLightningDetail(Map<String, dynamic> course) {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (sheetContext) => StatefulBuilder(builder: (context, setSheetState) {
        var joined = course['joined_by_me'] == true;
        return Padding(
          padding: const EdgeInsets.fromLTRB(24, 0, 24, 32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(course['name'].toString(), style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 8),
              Text('${course['start_name']} → ${course['destination_name']}'),
              Text('${course['event_date']} · 참가 ${course['participant_count']}명'),
              Text(course['ranking_mode'] == 'fastest'
                  ? '주행 시간이 짧은 순'
                  : '기준 시간에 가까운 순'),
              const SizedBox(height: 16),
              if (!joined)
                FilledButton.icon(
                  onPressed: () async {
                    await ref.read(apiClientProvider).post('/lightning-courses/${course['id']}/join');
                    course['joined_by_me'] = true;
                    setSheetState(() => joined = true);
                    ref.invalidate(lightningCoursesProvider);
                  },
                  icon: const Icon(Icons.group_add),
                  label: const Text('참가하기'),
                )
              else
                Row(children: [
                  Expanded(child: OutlinedButton.icon(
                    onPressed: () => showModalBottomSheet<void>(
                      context: context,
                      showDragHandle: true,
                      builder: (_) => RankingSheet.lightningCourse(
                        lightningCourseId: course['id'] as int,
                      ),
                    ),
                    icon: const Icon(Icons.emoji_events_outlined),
                    label: const Text('랭킹 보기'),
                  )),
                  const SizedBox(width: 8),
                  Expanded(child: FilledButton.icon(
                    onPressed: () {
                      final start = course['start'] as Map<String, dynamic>;
                      Navigator.pop(sheetContext);
                      startDriveFlow(context, ref, DriveTarget(
                        name: course['name'].toString(),
                        lightningCourseId: course['id'] as int,
                        start: NavigationPoint(
                          name: course['start_name'].toString(),
                          latitude: (start['latitude'] as num).toDouble(),
                          longitude: (start['longitude'] as num).toDouble(),
                        ),
                      ));
                    },
                    icon: const Icon(Icons.navigation),
                    label: const Text('주행 시작'),
                  )),
                ]),
            ],
          ),
        );
      }),
    );
  }
}

class _CourseMap extends StatelessWidget {
  const _CourseMap({
    required this.courses,
    required this.lightningCourses,
    required this.onCourseTap,
    required this.onLightningTap,
  });

  final List<Map<String, dynamic>> courses;
  final List<Map<String, dynamic>> lightningCourses;
  final ValueChanged<Map<String, dynamic>> onCourseTap;
  final ValueChanged<Map<String, dynamic>> onLightningTap;

  @override
  Widget build(BuildContext context) {
    if (courses.isEmpty && lightningCourses.isEmpty) {
      return const Center(child: Text('선택한 조건의 코스가 없습니다.'));
    }
    final center = _center;
    if (Platform.isAndroid) {
      return TmapNativeMap(
        centerLatitude: center.latitude,
        centerLongitude: center.longitude,
        zoom: 10,
        polylines: [
          ...courses.map((course) => _path(course)
              .map((point) => [point.latitude, point.longitude]).toList()),
          ...lightningCourses.map((course) {
            final start = course['start'] as Map<String, dynamic>;
            final end = course['destination'] as Map<String, dynamic>;
            return [
              [(start['latitude'] as num).toDouble(), (start['longitude'] as num).toDouble()],
              [(end['latitude'] as num).toDouble(), (end['longitude'] as num).toDouble()],
            ];
          }),
        ],
        markers: _nativeMarkers,
        onMarkerTap: (id) {
          final parts = id.split(':');
          final target = parts.first == 'course' ? courses : lightningCourses;
          final item = target.where((value) => value['id'].toString() == parts[1]).firstOrNull;
          if (item == null) return;
          parts.first == 'course' ? onCourseTap(item) : onLightningTap(item);
        },
      );
    }
    return FlutterMap(
      options: MapOptions(initialCenter: center, initialZoom: 10),
      children: [
        TileLayer(
          urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
          userAgentPackageName: 'com.waypoint.app',
        ),
        PolylineLayer(polylines: [
          ...courses.map((course) => Polyline(points: _path(course), color: Colors.blue, strokeWidth: 4)),
          ...lightningCourses.map((course) {
            final start = course['start'] as Map<String, dynamic>;
            final end = course['destination'] as Map<String, dynamic>;
            return Polyline(points: [
              LatLng((start['latitude'] as num).toDouble(), (start['longitude'] as num).toDouble()),
              LatLng((end['latitude'] as num).toDouble(), (end['longitude'] as num).toDouble()),
            ], color: Colors.orange, strokeWidth: 4);
          }),
        ]),
        MarkerLayer(markers: _flutterMarkers),
        const RichAttributionWidget(
          attributions: [TextSourceAttribution('OpenStreetMap contributors')],
        ),
      ],
    );
  }

  LatLng get _center {
    if (courses.isNotEmpty) return _path(courses.first).first;
    final start = lightningCourses.first['start'] as Map<String, dynamic>;
    return LatLng((start['latitude'] as num).toDouble(), (start['longitude'] as num).toDouble());
  }

  List<LatLng> _path(Map<String, dynamic> course) {
    final coordinates = (course['path'] as Map<String, dynamic>)['coordinates'] as List<dynamic>;
    return coordinates.map((raw) {
      final pair = raw as List<dynamic>;
      return LatLng((pair[0] as num).toDouble(), (pair[1] as num).toDouble());
    }).toList();
  }

  List<TmapNativeMarker> get _nativeMarkers => [
    for (final course in courses)
      for (final raw in course['navigation_anchors'] as List<dynamic>? ?? [])
        TmapNativeMarker(
          id: 'course:${course['id']}:${(raw as Map<String, dynamic>)['sequence']}',
          latitude: (raw['latitude'] as num).toDouble(),
          longitude: (raw['longitude'] as num).toDouble(),
          title: raw['name'].toString(),
          subtitle: course['name'].toString(),
          color: raw['anchor_type'].toString(),
        ),
    for (final course in lightningCourses)
      for (final type in ['start', 'destination'])
        TmapNativeMarker(
          id: 'lightning:${course['id']}:$type',
          latitude: ((course[type] as Map<String, dynamic>)['latitude'] as num).toDouble(),
          longitude: ((course[type] as Map<String, dynamic>)['longitude'] as num).toDouble(),
          title: course['${type}_name'].toString(),
          subtitle: course['name'].toString(),
          color: type,
        ),
  ];

  List<Marker> get _flutterMarkers => [
    for (final course in courses)
      for (final raw in course['navigation_anchors'] as List<dynamic>? ?? [])
        Marker(
          point: LatLng(
            ((raw as Map<String, dynamic>)['latitude'] as num).toDouble(),
            (raw['longitude'] as num).toDouble(),
          ),
          width: 48,
          height: 48,
          child: IconButton(
            onPressed: () => onCourseTap(course),
            icon: const Icon(Icons.location_on, color: Colors.blue),
          ),
        ),
    for (final course in lightningCourses)
      for (final type in ['start', 'destination'])
        Marker(
          point: LatLng(
            ((course[type] as Map<String, dynamic>)['latitude'] as num).toDouble(),
            ((course[type] as Map<String, dynamic>)['longitude'] as num).toDouble(),
          ),
          width: 48,
          height: 48,
          child: IconButton(
            onPressed: () => onLightningTap(course),
            icon: const Icon(Icons.bolt, color: Colors.orange),
          ),
        ),
  ];
}
