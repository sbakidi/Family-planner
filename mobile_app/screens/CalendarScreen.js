import React, { useEffect, useState } from 'react';
import { View, Text, FlatList, StyleSheet } from 'react-native';
import apiClient from '../api/client';

export default function CalendarScreen({ route }) {
  const { userId } = route.params;
  const [events, setEvents] = useState([]);

  useEffect(() => {
    apiClient
      .getUserEvents(userId)
      .then(setEvents)
      .catch(() => setEvents([]));
  }, [userId]);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Events</Text>
      <FlatList
        data={events}
        keyExtractor={(item) => String(item.id)}
        renderItem={({ item }) => (
          <View style={styles.item}>
            <Text style={styles.itemTitle}>{item.title}</Text>
            <Text>{item.start_time}</Text>
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
  },
  title: {
    fontSize: 24,
    marginBottom: 16,
  },
  item: {
    padding: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#ccc',
  },
  itemTitle: {
    fontWeight: 'bold',
  },
});
