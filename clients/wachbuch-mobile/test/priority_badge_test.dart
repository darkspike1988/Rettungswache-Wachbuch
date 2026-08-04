import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:wachbuch_mobile/ui/priority_badge.dart';

void main() {
  group('PriorityBadge', () {
    Widget wrap(Widget child) {
      return MaterialApp(
        home: Scaffold(body: Center(child: child)),
      );
    }

    testWidgets('renders urgent label and dot', (tester) async {
      await tester.pumpWidget(wrap(const PriorityBadge(priority: 'urgent')));
      expect(find.text('Dringend'), findsOneWidget);
      expect(find.byType(Container), findsWidgets);
    });

    testWidgets('renders important label', (tester) async {
      await tester.pumpWidget(wrap(const PriorityBadge(priority: 'important')));
      expect(find.text('Wichtig'), findsOneWidget);
    });

    testWidgets('renders custom label when provided', (tester) async {
      await tester.pumpWidget(wrap(const PriorityBadge(priority: 'urgent', label: 'ASAP')));
      expect(find.text('ASAP'), findsOneWidget);
    });

    testWidgets('compact mode has smaller text', (tester) async {
      await tester.pumpWidget(wrap(const PriorityBadge(priority: 'normal', compact: true)));
      final text = tester.widget<Text>(find.text('Normal'));
      expect(text.style?.fontSize, lessThanOrEqualTo(12));
    });
  });
}
