/**
 * 通用表格排序 composable
 * 用法：
 *   const { sortState, handleSortChange, applySort } = useTableSort()
 *   <el-table @sort-change="handleSortChange">
 *     <el-table-column prop="x" sortable="custom" />
 *   </el-table>
 *   const sorted = applySort(originalList)
 */
import { ref } from 'vue'

export interface SortState {
  prop: string
  order: 'ascending' | 'descending' | null
}

export function useTableSort() {
  const sortState = ref<SortState>({ prop: '', order: null })

  function handleSortChange({ prop, order }: { prop: string; order: 'ascending' | 'descending' | null }) {
    sortState.value = { prop, order }
  }

  function applySort<T extends Record<string, any>>(list: T[]): T[] {
    const { prop, order } = sortState.value
    if (!prop || !order) return list
    const arr = [...list]
    const dir = order === 'ascending' ? 1 : -1
    arr.sort((a, b) => {
      const va = a?.[prop]
      const vb = b?.[prop]
      // null/undefined 排到末尾
      if (va == null && vb == null) return 0
      if (va == null) return 1
      if (vb == null) return -1
      // 数字
      if (typeof va === 'number' && typeof vb === 'number') {
        return (va - vb) * dir
      }
      // 字符串
      const sa = String(va)
      const sb = String(vb)
      // 数字字符串按数字比
      const na = Number(sa)
      const nb = Number(sb)
      if (!Number.isNaN(na) && !Number.isNaN(nb) && /^-?\d+(\.\d+)?$/.test(sa) && /^-?\d+(\.\d+)?$/.test(sb)) {
        return (na - nb) * dir
      }
      // 日期字符串（YYYY-MM-DD 或含时间）按时间比
      if (/^\d{4}-\d{2}-\d{2}/.test(sa) && /^\d{4}-\d{2}-\d{2}/.test(sb)) {
        return (sa < sb ? -1 : sa > sb ? 1 : 0) * dir
      }
      // 普通字符串
      return sa.localeCompare(sb, 'zh-CN') * dir
    })
    return arr
  }

  function reset() {
    sortState.value = { prop: '', order: null }
  }

  return { sortState, handleSortChange, applySort, reset }
}
