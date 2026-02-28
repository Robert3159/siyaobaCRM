<script setup lang="ts">
defineOptions({
  name: 'SystemAbout'
});
</script>

<template>
  <div class="flex-col-stretch gap-16px">
    <NCard :bordered="false" title="About Siyaoba CRM">
      <p class="text-15px text-[#4e5969] leading-7">
        Siyaoba CRM is an internal management system for team collaboration, business process management, and data
        tracking.
      </p>
    </NCard>

    <NCard :bordered="false" title="Version Info">
      <NDescriptions label-placement="left" bordered :column="1">
        <NDescriptionsItem label="Frontend">Soybean Admin (Vue 3 + TypeScript)</NDescriptionsItem>
        <NDescriptionsItem label="Backend">FastAPI</NDescriptionsItem>
        <NDescriptionsItem label="Environment">Static Route Mode</NDescriptionsItem>
      </NDescriptions>
    </NCard>
  </div>
</template>

<style scoped></style>
