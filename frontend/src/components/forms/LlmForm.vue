<template><NodeSemanticForm v-bind="$props" /></template>
<script setup lang="ts">import NodeSemanticForm from './NodeSemanticForm.vue'; import type { GraphNode } from '@/types/graph'; defineProps<{ node: GraphNode }>()</script>
