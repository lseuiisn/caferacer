import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/cafe_api.dart';
import 'cafe_list_state.dart';

class CafeListController extends StateNotifier<CafeListState> {
  CafeListController(this._api) : super(const CafeListState()) {
    loadFirstPage();
  }

  final CafeApi _api;

  Future<void> loadFirstPage() async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final result = await _api.fetchCafes(page: 1, size: state.pageSize);
      state = state.copyWith(
        cafes: result.items,
        page: 1,
        total: result.meta.total,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, errorMessage: e.toString());
    }
  }

  Future<void> loadNextPage() async {
    if (state.isLoadingMore || !state.hasMore) return;
    state = state.copyWith(isLoadingMore: true, clearError: true);
    try {
      final nextPage = state.page + 1;
      final result = await _api.fetchCafes(
        page: nextPage,
        size: state.pageSize,
      );
      state = state.copyWith(
        cafes: [...state.cafes, ...result.items],
        page: nextPage,
        total: result.meta.total,
        isLoadingMore: false,
      );
    } catch (e) {
      state = state.copyWith(isLoadingMore: false, errorMessage: e.toString());
    }
  }

  Future<void> refresh() => loadFirstPage();
}
