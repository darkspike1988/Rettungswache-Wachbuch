import 'package:flutter/material.dart';

import '../theme/design_tokens.dart';

class StatusChip extends StatelessWidget {
  const StatusChip({
    super.key,
    required this.status,
    this.label,
  });

  final String status;
  final String? label;

  @override
  Widget build(BuildContext context) {
    final color = WachbuchTokens.statusColor(status);
    final text = label ?? _defaultLabel(status);

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: WachbuchTokens.spaceMd,
        vertical: 6,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(WachbuchTokens.radiusMd),
      ),
      constraints: const BoxConstraints(minHeight: 36),
      child: Text(
        text,
        style: TextStyle(
          color: color,
          fontSize: WachbuchTokens.textBody,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }

  String _defaultLabel(String s) {
    return switch (s) {
      'open' || 'new' => 'Offen',
      'in_progress' || 'active' => 'In Arbeit',
      'done' || 'closed' => 'Erledigt',
      _ => 'Unbekannt',
    };
  }
}
