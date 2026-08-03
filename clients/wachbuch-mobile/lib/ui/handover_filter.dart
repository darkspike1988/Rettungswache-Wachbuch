String handoverStatusLabel(Object? value) => _enumLabel(value, const {
  'open': 'Offen',
  'in_progress': 'In Bearbeitung',
  'done': 'Erledigt',
});

String handoverPriorityLabel(Object? value) => _enumLabel(value, const {
  'normal': 'Normal',
  'important': 'Wichtig',
  'urgent': 'Dringend',
});

String handoverCategoryLabel(Object? value) => _enumLabel(value, const {
  'station': 'Wache',
  'vehicle': 'Fahrzeugstatus',
  'material': 'Material',
  'task': 'Offene Aufgabe',
  'safety': 'Sicherheit/Mangel',
});

List<Map<String, dynamic>> filterHandovers(
  List<Map<String, dynamic>> items, {
  String query = '',
  Set<String> statuses = const {},
  Set<String> priorities = const {},
}) {
  final normalizedQuery = query.trim().toLowerCase();

  return items
      .where((item) {
        final status = _raw(item['status']);
        final priority = _raw(item['priority']);
        if (statuses.isNotEmpty && !statuses.contains(status)) {
          return false;
        }
        if (priorities.isNotEmpty && !priorities.contains(priority)) {
          return false;
        }
        if (normalizedQuery.isEmpty) {
          return true;
        }

        final searchable = [
          _raw(item['title']),
          _raw(item['category']),
          handoverCategoryLabel(item['category']).toLowerCase(),
          handoverStatusLabel(item['status']).toLowerCase(),
          handoverPriorityLabel(item['priority']).toLowerCase(),
        ].join(' ');
        return searchable.contains(normalizedQuery);
      })
      .toList(growable: false);
}

String _raw(Object? value) => value?.toString().trim().toLowerCase() ?? '';

String _enumLabel(Object? value, Map<String, String> labels) {
  final raw = _raw(value);
  if (raw.isEmpty) {
    return 'Nicht angegeben';
  }
  final known = labels[raw];
  if (known != null) {
    return known;
  }
  return raw
      .split(RegExp(r'[_\s-]+'))
      .where((part) => part.isNotEmpty)
      .map((part) => '${part[0].toUpperCase()}${part.substring(1)}')
      .join(' ');
}
