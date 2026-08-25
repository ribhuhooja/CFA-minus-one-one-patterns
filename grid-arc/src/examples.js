/** Built-in arcs, shared by the UI and the test harness. */
export const EXAMPLES = [
  { name: 'simple bubble — final step W', expect: 'E N W',
    arc: [[5.4, 5], [5.6, 5.5], [5.4, 6]] },
  { name: 'staircase — final step W', expect: 'E E N W',
    arc: [[5.423, 11], [5.622, 11.396], [6, 11.233], [6.719, 11.71], [6.731, 12]] },
  { name: 'long climb — 8 steps', expect: 'E N N E N E N W',
    arc: [[9.761, 8], [9.445, 8.37], [9.749, 9], [9.282, 9.415], [9.548, 10], [9.401, 10.538],
          [10, 10.458], [10.626, 10.487], [10.725, 11], [10.668, 11.323], [11, 11.273],
          [11.65, 11.44], [11.343, 12]] },
  { name: 'first partial edge S', expect: 'S E N N',
    arc: [[12, 12.569], [13, 13.288]] },
  { name: 'same edge, no lattice point — final step S', expect: 'S',
    arc: [[5, 5.7], [5.5, 5.65], [5.6, 5.35], [5, 5.3]] },
  { name: 'same edge, no lattice point — final step N', expect: 'N',
    arc: [[12, 12.508], [11.389, 13.558], [11.771, 13.049], [12, 12.629]] },
  { name: 'no solution — D swallows a forbidden point', expect: null,
    arc: [[4, 10.64], [4.457, 10.413], [4.699, 9.686], [5, 9.623], [5.684, 9.647], [6, 9.253]] },
  { name: 'no solution — forced first partial edge is crossed', expect: null,
    arc: [[8.784, 8], [8.705, 7.559], [10, 7.351]] }
];
export default EXAMPLES;
