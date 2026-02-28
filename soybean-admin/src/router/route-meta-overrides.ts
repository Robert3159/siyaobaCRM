import type { ElegantConstRoute } from '@elegant-router/types';

export type RouteMetaOverride = {
  meta?: Partial<{
    order: number;
    icon: string;
    constant: boolean;
    hideInMenu: boolean;
    keepAlive: boolean;
    [key: string]: unknown;
  }>;
  redirect?: { name: string };
};

export const routeMetaOverrides: Record<string, RouteMetaOverride> = {
  'player-list': {
    meta: { constant: true, hideInMenu: true }
  },

  home: { meta: { order: 6, icon: 'mdi:monitor-dashboard', hideInMenu: true } },
  dashboard: {
    meta: { order: 1, icon: 'mdi:chart-box-outline' }
  },
  qgs: {
    meta: { order: 2, icon: 'mdi:bullhorn-outline' },
    redirect: { name: 'dashboard_qgs' }
  },
  hgs: {
    meta: { order: 3, icon: 'mdi:account-group-outline' },
    redirect: { name: 'dashboard_hgs' }
  },
  business: { meta: { order: 4, icon: 'mdi:briefcase-outline' } },
  system: { meta: { order: 5, icon: 'mdi:cog-outline' } },

  dashboard_overall: { meta: { order: 1, icon: 'mdi:chart-box-multiple' } },
  dashboard_qgs: { meta: { order: 2, icon: 'mdi:chart-areaspline' } },
  dashboard_hgs: { meta: { order: 3, icon: 'mdi:chart-areaspline' } },

  qgs_submit: { meta: { order: 1, icon: 'mdi:plus-box' } },
  qgs_list: { meta: { order: 2, icon: 'mdi:format-list-bulleted-square' } },
  qgs_statistics: { meta: { order: 3, icon: 'mdi:calendar-month' } },

  hgs_list: { meta: { order: 1, icon: 'mdi:format-list-bulleted-square' } },
  hgs_order: { meta: { order: 2, icon: 'mdi:order-bool-ascending' } },
  hgs_statistics: { meta: { order: 3, icon: 'mdi:calendar-month' } },

  business_project: { meta: { order: 1, icon: 'mdi:bag-checked' } },
  business_schema: { meta: { order: 2, icon: 'mdi:form-select' } },

  system_user: { meta: { order: 2, icon: 'mdi:account-multiple' } },
  system_role: { meta: { order: 3, icon: 'mdi:book-account' } },
  system_menu: { meta: { order: 4, icon: 'mdi:menu-open', hideInMenu: true } },
  system_log: { meta: { order: 5, icon: 'mdi:file-document-outline' } },
  system_profile: { meta: { order: 6, icon: 'mdi:account-circle' } },
  system_about: { meta: { order: 7, icon: 'mdi:information-outline' } }
};

export function applyRouteMetaOverrides(
  routes: ElegantConstRoute[],
  overrides: Record<string, RouteMetaOverride>
): ElegantConstRoute[] {
  return routes.map(route => {
    const override = overrides[route.name as string];
    const nextMeta = override?.meta ? { ...route.meta, ...override.meta } : route.meta;
    const nextRedirect = override?.redirect ?? route.redirect;
    const nextChildren =
      route.children && route.children.length > 0 ? applyRouteMetaOverrides(route.children, overrides) : route.children;

    return {
      ...route,
      meta: nextMeta,
      ...(nextRedirect !== undefined && { redirect: nextRedirect }),
      ...(nextChildren !== undefined && { children: nextChildren })
    } as ElegantConstRoute;
  });
}
