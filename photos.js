// photos.js - Single source of truth for all photo data
// To add a new photo: add an entry to the PHOTOS array below

const PRINT_SIZES = [
    { id: 'a4', label: 'A4 (21 x 29.7 cm)', multiplier: 0.7 },
    { id: 'a3', label: 'A3 (29.7 x 42 cm)', multiplier: 1.0 },
    { id: 'a2', label: 'A2 (42 x 59.4 cm)', multiplier: 1.5 },
    { id: 'custom', label: 'Other size - Contact me', multiplier: null }
];

const PHOTOS = [
    {
        id: 'I',
        key: 'print1',
        src: 'img/img1.jpg',
        title: 'Island Dreams',
        location: 'Madeira',
        date: 'March 2023',
        basePrice: 50,
        story: 'The Atlantic fog rolled in like a whisper, transforming the familiar landscape into something otherworldly. Standing on these volcanic cliffs, I understood why sailors once believed this was the edge of the world.'
    },
    {
        id: 'II',
        key: 'print2',
        src: 'img/img2.jpg',
        title: 'Road to Nowhere',
        location: 'Madeira',
        date: 'March 2023',
        basePrice: 50,
        story: 'Some roads lead to destinations; others lead to discoveries. This mountain pass, shrouded in mist, reminded me that the journey itself can be the destination.'
    },
    {
        id: 'III',
        key: 'print3',
        src: 'img/img3.jpg',
        title: 'After the Fire',
        location: 'Madeira',
        date: 'March 2023',
        basePrice: 50,
        story: 'Nature has a way of reclaiming what was lost. These burnt slopes, scarred but not defeated, spoke of resilience and the endless cycle of destruction and rebirth.'
    },
    {
        id: 'IV',
        key: 'print4',
        src: 'img/img4.jpg',
        title: 'Persian Twilight',
        location: 'Shiraz, Iran',
        date: 'November 2022',
        basePrice: 60,
        story: 'From my hotel window, the ancient city of poets sprawled beneath a modernizing skyline. Shiraz at dusk is a conversation between past and present, each building a verse in an ongoing poem.'
    },
    {
        id: 'V',
        key: 'print5',
        src: 'img/img5.jpg',
        title: 'Journey Within',
        location: 'Shiraz, Iran',
        date: 'November 2022',
        basePrice: 60,
        story: 'In the back of a taxi, crossing a city of gardens and verses, I caught a glimpse of contemplation. Sometimes the most profound journeys happen while sitting still.'
    },
    {
        id: 'VI',
        key: 'print6',
        src: 'img/img6.jpg',
        title: 'City of a Thousand Hills',
        location: 'Antananarivo, Madagascar',
        date: 'June 2022',
        basePrice: 55,
        story: 'They call it Tana, and from above, you understand why it sprawls across twelve sacred hills. Each neighborhood tells its own story, each rooftop holds its own dreams.'
    },
    {
        id: 'VII',
        key: 'print7',
        src: 'img/img7.jpg',
        title: 'Rural Rhythms',
        location: 'Madagascar',
        date: 'June 2022',
        basePrice: 55,
        story: 'Life moves differently in the highlands. Here, time is measured not in hours but in harvests, not in deadlines but in seasons.'
    },
    {
        id: 'VIII',
        key: 'print8',
        src: 'img/img8.jpg',
        title: 'River Journey',
        location: 'Madagascar',
        date: 'June 2022',
        basePrice: 55,
        story: 'The Pangalanes Canal cuts through the heart of the rainforest. From our pirogue, the world was reduced to water, green, and the sound of paddles breaking the surface.'
    },
    {
        id: 'IX',
        key: 'print9',
        src: 'img/img9.jpg',
        title: 'Green Cathedral',
        location: 'Madagascar',
        date: 'June 2022',
        basePrice: 55,
        story: 'In the forest, silence has texture. Every leaf filters light differently, every shadow holds a secret. This is where the earth breathes.'
    },
    {
        id: 'X',
        key: 'print10',
        src: 'img/img10.jpg',
        title: 'Arctic Night',
        location: 'Tromsø, Norway',
        date: 'January 2022',
        basePrice: 65,
        story: 'Above the Arctic Circle, darkness isn\'t the absence of light—it\'s a canvas. The snow reflects what little light exists, creating a world painted in shades of blue.'
    },
    {
        id: 'XI',
        key: 'print11',
        src: 'img/img11.jpg',
        title: 'Hope and Change',
        location: 'Atlanta to Washington D.C.',
        date: 'January 2009',
        basePrice: 50,
        story: 'On a bus filled with strangers who felt like family, we traveled through the night toward history. The inauguration wasn\'t just about one man; it was about the possibility of transformation.'
    },
    {
        id: 'XII',
        key: 'print12',
        src: 'img/img12.jpg',
        title: 'Monuments and Moments',
        location: 'Washington D.C.',
        date: 'January 2009',
        basePrice: 50,
        story: 'In the shadow of monuments to the past, we gathered to witness the future. The Lincoln Memorial had seen many crowds, but this one carried a different energy.'
    },
    {
        id: 'XIII',
        key: 'print13',
        src: 'img/img13.jpg',
        title: 'Congo Roads',
        location: 'Outside Kinshasa, Congo',
        date: 'August 2021',
        basePrice: 60,
        story: 'The road from Kinshasa tests both vehicle and spirit. But in the midst of the journey, there are moments of unexpected grace—a smile, a story, a shared understanding.'
    },
    {
        id: 'XIV',
        key: 'print14',
        src: 'img/img14.jpg',
        title: 'Frozen Fjord',
        location: 'Tromsø, Norway',
        date: 'January 2022',
        basePrice: 65,
        story: 'When the sea itself seems to pause, held in winter\'s grip, you realize that even the eternal can be transformed. The fjords in winter are nature\'s meditation on stillness.'
    }
];
