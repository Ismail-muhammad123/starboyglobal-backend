// Theme-aware Chart.js Helper Utilities
window.PortalCharts = (function () {
  function getThemeColors() {
    const isDark = (document.documentElement.getAttribute('data-theme') || 'dark') === 'dark';
    return {
      text: isDark ? '#94A3B8' : '#475569',
      border: isDark ? '#1E3A5F' : '#E2E8F0',
      accent: isDark ? '#3B82F6' : '#1D4ED8',
      accentBg: isDark ? 'rgba(59, 130, 246, 0.2)' : 'rgba(29, 78, 216, 0.1)',
      success: isDark ? '#10B981' : '#059669',
      warning: isDark ? '#F59E0B' : '#D97706',
      danger: isDark ? '#EF4444' : '#DC2626',
      purple: isDark ? '#8B5CF6' : '#6D28D9',
      cyan: isDark ? '#06B6D4' : '#0891B2',
    };
  }

  function createLineChart(ctx, labels, dataSets) {
    if (typeof Chart === 'undefined') return null;
    const colors = getThemeColors();

    const formattedDataSets = dataSets.map((ds) => {
      const isProfitLoss = ds.label && ds.label.includes('Profit');
      const baseConfig = {
        label: ds.label,
        data: ds.data,
        borderColor: ds.borderColor || colors.accent,
        backgroundColor: ds.backgroundColor || colors.accentBg,
        fill: ds.fill !== undefined ? ds.fill : true,
        tension: 0.35,
        borderWidth: 2.5,
        pointRadius: 3,
        pointHoverRadius: 6
      };

      if (isProfitLoss) {
        baseConfig.segment = {
          borderColor: (c) => ((c.p0.parsed.y < 0 || c.p1.parsed.y < 0) ? '#EF4444' : '#10B981')
        };
        baseConfig.pointBackgroundColor = (c) => (c.raw < 0 ? '#EF4444' : '#10B981');
        baseConfig.pointBorderColor = (c) => (c.raw < 0 ? '#EF4444' : '#10B981');
      }

      return { ...baseConfig, ...ds };
    });

    const chart = new Chart(ctx, {
      type: 'line',
      data: { labels, datasets: formattedDataSets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: { color: colors.text, font: { family: 'system-ui', size: 12 } }
          },
          tooltip: {
            mode: 'index',
            intersect: false,
            callbacks: {
              label: function(context) {
                let label = context.dataset.label || '';
                if (label) label += ': ';
                if (context.parsed.y !== null) {
                  const val = context.parsed.y;
                  label += (val < 0 ? '-₦' + Math.abs(val).toLocaleString() : '₦' + val.toLocaleString());
                }
                return label;
              }
            }
          }
        },
        scales: {
          x: {
            grid: { color: colors.border, drawBorder: false },
            ticks: { color: colors.text }
          },
          y: {
            grid: { color: colors.border, drawBorder: false },
            ticks: {
              color: colors.text,
              callback: (val) => (val < 0 ? '-₦' + Math.abs(val).toLocaleString() : '₦' + val.toLocaleString())
            }
          }
        }
      }
    });

    window.addEventListener('themechange', () => {
      const tc = getThemeColors();
      if (chart.options.scales.x) chart.options.scales.x.ticks.color = tc.text;
      if (chart.options.scales.y) chart.options.scales.y.ticks.color = tc.text;
      if (chart.options.plugins.legend) chart.options.plugins.legend.labels.color = tc.text;
      chart.update();
    });

    return chart;
  }

  function createDoughnutChart(ctx, labels, data, bgColors) {
    if (typeof Chart === 'undefined') return null;
    const colors = getThemeColors();

    const chart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [{
          data: data,
          backgroundColor: bgColors || [colors.accent, colors.success, colors.warning, colors.danger, colors.purple, colors.cyan],
          borderWidth: 2,
          borderColor: colors.border
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'right',
            labels: { color: colors.text, font: { family: 'system-ui', size: 11 } }
          }
        },
        cutout: '70%'
      }
    });

    return chart;
  }

  function createBarChart(ctx, labels, data, bgColors) {
    if (typeof Chart === 'undefined') return null;
    const colors = getThemeColors();

    const chart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Volume (₦)',
          data: data,
          backgroundColor: bgColors || [colors.accent, colors.success, colors.warning, colors.danger, colors.purple, colors.cyan],
          borderWidth: 1,
          borderRadius: 6,
          borderColor: colors.border
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            callbacks: {
              label: (item) => 'Volume: ₦' + (item.raw || 0).toLocaleString()
            }
          }
        },
        scales: {
          x: {
            grid: { color: colors.border, drawBorder: false },
            ticks: { color: colors.text, font: { size: 11 } }
          },
          y: {
            grid: { color: colors.border, drawBorder: false },
            ticks: {
              color: colors.text,
              callback: (val) => '₦' + val.toLocaleString()
            }
          }
        }
      }
    });

    return chart;
  }

  return {
    createLineChart: createLineChart,
    createDoughnutChart: createDoughnutChart,
    createBarChart: createBarChart,
    getThemeColors: getThemeColors
  };
})();
