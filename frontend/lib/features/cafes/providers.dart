import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'application/cafe_list_controller.dart';
import 'application/cafe_list_state.dart';
import 'data/cafe_api.dart';

final cafeApiProvider = Provider<CafeApi>((ref) => CafeApi());

final cafeListControllerProvider =
    StateNotifierProvider<CafeListController, CafeListState>((ref) {
      return CafeListController(ref.watch(cafeApiProvider));
    });
