class Checklist {
  const Checklist({
    required this.id,
    required this.title,
    this.items = const [],
    this.completed = false,
    this.completedAt,
    this.description = '',
    this.interval = '',
    this.dueNext,
    this.overdue = false,
  });

  factory Checklist.fromJson(Map<String, dynamic> json) {
    final dueNext = _readDate(json['due_next'] ?? json['dueNext']);
    final overdueFlag = json['overdue'] == true || json['is_overdue'] == true;
    return Checklist(
      id: _readInt(json['id']),
      title: (json['title'] ?? json['name'] ?? '').toString().trim(),
      description: (json['description'] ?? '').toString().trim(),
      items: _readItems(json['items'] ?? json['tasks'] ?? const []),
      completed: json['completed'] == true || json['is_completed'] == true,
      completedAt: _readDate(json['completed_at']) ??
          _readDate((json['completion'] is Map
                  ? (json['completion'] as Map)['created_at']
                  : null)),
      interval: _readInterval(json['interval']),
      dueNext: dueNext,
      overdue: overdueFlag || _isPastDue(dueNext),
    );
  }

  final int id;
  final String title;
  final String description;
  final List<ChecklistItem> items;
  final bool completed;
  final DateTime? completedAt;
  /// `daily` | `weekly` | `monthly` | empty when not recurring.
  final String interval;
  final DateTime? dueNext;
  final bool overdue;

  int get checkedCount => items.where((item) => item.checked).length;

  bool get allChecked => items.isNotEmpty && items.every((item) => item.checked);

  bool get isRecurring => interval.isNotEmpty;

  bool get isDueToday {
    if (completed) return false;
    if (overdue) return true;
    final due = dueNext;
    if (due == null) return false;
    final now = DateTime.now();
    return due.year == now.year && due.month == now.month && due.day == now.day;
  }

  Checklist copyWith({
    int? id,
    String? title,
    String? description,
    List<ChecklistItem>? items,
    bool? completed,
    DateTime? completedAt,
    String? interval,
    DateTime? dueNext,
    bool? overdue,
  }) {
    return Checklist(
      id: id ?? this.id,
      title: title ?? this.title,
      description: description ?? this.description,
      items: items ?? this.items,
      completed: completed ?? this.completed,
      completedAt: completedAt ?? this.completedAt,
      interval: interval ?? this.interval,
      dueNext: dueNext ?? this.dueNext,
      overdue: overdue ?? this.overdue,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is Checklist && runtimeType == other.runtimeType && id == other.id;

  @override
  int get hashCode => id.hashCode;
}

class ChecklistItem {
  const ChecklistItem({
    required this.id,
    required this.label,
    this.checked = false,
    this.note = '',
  });

  factory ChecklistItem.fromJson(Map<String, dynamic> json) {
    return ChecklistItem(
      id: _readInt(json['id']),
      label: (json['label'] ?? json['title'] ?? json['text'] ?? '').toString().trim(),
      checked: json['checked'] == true || json['done'] == true,
      note: (json['note'] ?? '').toString().trim(),
    );
  }

  final int id;
  final String label;
  final bool checked;
  final String note;
}

List<ChecklistItem> _readItems(Object? value) {
  if (value is! List) return const [];
  return value
      .whereType<Map>()
      .map((item) => ChecklistItem.fromJson(Map<String, dynamic>.from(item)))
      .toList(growable: false);
}

DateTime? _readDate(Object? value) {
  if (value == null) return null;
  return DateTime.tryParse(value.toString())?.toLocal();
}

bool _isPastDue(DateTime? due) {
  if (due == null) return false;
  final today = DateTime.now();
  final dueDay = DateTime(due.year, due.month, due.day);
  final todayDay = DateTime(today.year, today.month, today.day);
  return dueDay.isBefore(todayDay);
}

String _readInterval(Object? value) {
  final raw = value?.toString().trim().toLowerCase() ?? '';
  return switch (raw) {
    'daily' || 'weekly' || 'monthly' => raw,
    _ => '',
  };
}

int _readInt(Object? value) {
  if (value is int) return value;
  return int.tryParse(value?.toString() ?? '') ?? 0;
}
