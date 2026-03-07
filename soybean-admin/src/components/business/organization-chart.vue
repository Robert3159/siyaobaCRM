<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { VueFlow, useVueFlow } from '@vue-flow/core';
import { Background } from '@vue-flow/background';
import { Controls } from '@vue-flow/controls';
import '@vue-flow/core/dist/style.css';
import '@vue-flow/core/dist/theme-default.css';
import '@vue-flow/controls/dist/style.css';

interface Props {
  users: Api.User.UserItem[];
}

const props = defineProps<Props>();

const { fitView } = useVueFlow();

const nodes = computed(() => {
  const result: any[] = [];
  const levelMap = new Map<number, number>();
  const positionMap = new Map<number, { x: number; y: number }>();

  function calculateLevel(userId: number, visited = new Set<number>()): number {
    if (visited.has(userId)) return 0;
    if (levelMap.has(userId)) return levelMap.get(userId)!;

    visited.add(userId);
    const user = props.users.find(u => u.id === userId);
    if (!user || !user.manager_id) {
      levelMap.set(userId, 0);
      return 0;
    }

    const level = calculateLevel(user.manager_id, visited) + 1;
    levelMap.set(userId, level);
    return level;
  }

  props.users.forEach(user => calculateLevel(user.id));

  const levelGroups = new Map<number, number[]>();
  props.users.forEach(user => {
    const level = levelMap.get(user.id) || 0;
    if (!levelGroups.has(level)) levelGroups.set(level, []);
    levelGroups.get(level)!.push(user.id);
  });

  levelGroups.forEach((userIds, level) => {
    const count = userIds.length;
    const startX = -(count - 1) * 150;
    userIds.forEach((userId, index) => {
      positionMap.set(userId, {
        x: startX + index * 300,
        y: level * 150
      });
    });
  });

  props.users.forEach(user => {
    const pos = positionMap.get(user.id) || { x: 0, y: 0 };
    let roleColor = '#e5e7eb';
    if (user.role?.includes('ADMIN')) {
      roleColor = '#fed7aa';
    } else if (user.role?.startsWith('QGS')) {
      roleColor = '#bfdbfe';
    } else if (user.role?.startsWith('HGS')) {
      roleColor = '#ddd6fe';
    }

    result.push({
      id: String(user.id),
      type: 'default',
      position: pos,
      data: {
        label: `${user.alias || user.user}\n${user.role || '-'}`
      },
      style: {
        background: roleColor,
        border: '1px solid #999',
        borderRadius: '8px',
        padding: '10px',
        fontSize: '12px',
        width: '120px',
        textAlign: 'center'
      }
    });
  });

  return result;
});

const edges = computed(() => {
  return props.users
    .filter(user => user.manager_id)
    .map(user => ({
      id: `e${user.manager_id}-${user.id}`,
      source: String(user.manager_id),
      target: String(user.id),
      type: 'smoothstep',
      animated: false
    }));
});

onMounted(() => {
  setTimeout(() => fitView({ padding: 0.2 }), 100);
});
</script>

<template>
  <div class="h-600px w-full">
    <VueFlow :nodes="nodes" :edges="edges" :fit-view-on-init="true">
      <Background />
      <Controls />
    </VueFlow>
  </div>
</template>
