// photos.js - Single source of truth for all photo data
// To add a new photo: add an entry to the PHOTOS array below.
// To change the rotating hero set, edit HERO_PHOTO_KEYS. One is picked at random per page load.

const HERO_PHOTO_KEYS = ['print20', 'print13', 'print8', 'print2'];

const PRINT_SIZES = [
    { id: 'a4', label: 'A4 (21 x 29.7 cm)', multiplier: 0.7 },
    { id: 'a3', label: 'A3 (29.7 x 42 cm)', multiplier: 1.0 },
    { id: 'a2', label: 'A2 (42 x 59.4 cm)', multiplier: 1.5 },
    { id: 'custom', label: 'Other size - Contact me', multiplier: null }
];

// Order is the curated display sequence. The `id` (Roman numeral) tracks position
// for the purchase dropdown. The `key` is the stable identifier and ties to the URL
// deep-link, so existing print URLs keep working even after a reorder.
const PHOTOS = [
    {
        id: 'I',
        key: 'print2',
        src: 'img/img2.jpg',
        location: 'Madeira',
        date: 'August 2015',
        basePrice: 50
    },
    {
        id: 'II',
        key: 'print17',
        src: 'img/img17.jpg',
        location: 'Iceland',
        date: 'August 2024',
        basePrice: 65
    },
    {
        id: 'III',
        key: 'print15',
        src: 'img/img15.jpg',
        location: 'Iceland',
        date: 'August 2024',
        basePrice: 65
    },
    {
        id: 'IV',
        key: 'print5',
        src: 'img/img5.jpg',
        location: 'Shiraz, Iran',
        date: 'April 2016',
        basePrice: 60
    },
    {
        id: 'V',
        key: 'print11',
        src: 'img/img11.jpg',
        location: 'Atlanta to Washington D.C.',
        date: 'January 2009',
        basePrice: 50
    },
    {
        id: 'VI',
        key: 'print20',
        src: 'img/img20.jpg',
        location: 'Iceland',
        date: 'August 2024',
        basePrice: 65
    },
    {
        id: 'VII',
        key: 'print7',
        src: 'img/img7.jpg',
        location: 'Madagascar',
        date: 'June 2016',
        basePrice: 55
    },
    {
        id: 'VIII',
        key: 'print16',
        src: 'img/img16.jpg',
        location: 'Iceland',
        date: 'August 2024',
        basePrice: 65
    },
    {
        id: 'IX',
        key: 'print19',
        src: 'img/img19.jpg',
        location: 'Iceland',
        date: 'August 2024',
        basePrice: 65
    },
    {
        id: 'X',
        key: 'print8',
        src: 'img/img8.jpg',
        location: 'Madagascar',
        date: 'June 2016',
        basePrice: 55
    },
    {
        id: 'XI',
        key: 'print9',
        src: 'img/img9.jpg',
        location: 'Madagascar',
        date: 'June 2016',
        basePrice: 55
    },
    {
        id: 'XII',
        key: 'print13',
        src: 'img/img13.jpg',
        location: 'Outside Kinshasa, Congo',
        date: 'February 2011',
        basePrice: 60
    },
    {
        id: 'XIII',
        key: 'print12',
        src: 'img/img12.jpg',
        location: 'Washington D.C.',
        date: 'January 2009',
        basePrice: 50
    },
    {
        id: 'XIV',
        key: 'print1',
        src: 'img/img1.jpg',
        location: 'Madeira',
        date: 'August 2015',
        basePrice: 50
    },
    {
        id: 'XV',
        key: 'print18',
        src: 'img/img18.jpg',
        location: 'Iceland',
        date: 'August 2024',
        basePrice: 65
    },
    {
        id: 'XVI',
        key: 'print4',
        src: 'img/img4.jpg',
        location: 'Shiraz, Iran',
        date: 'April 2016',
        basePrice: 60
    },
    {
        id: 'XVII',
        key: 'print6',
        src: 'img/img6.jpg',
        location: 'Antananarivo, Madagascar',
        date: 'June 2016',
        basePrice: 55
    },
    {
        id: 'XVIII',
        key: 'print3',
        src: 'img/img3.jpg',
        location: 'Madeira',
        date: 'August 2015',
        basePrice: 50
    },
    {
        id: 'XIX',
        key: 'print10',
        src: 'img/img10.jpg',
        location: 'Tromsø, Norway',
        date: 'January 2009',
        basePrice: 65
    },
    {
        id: 'XX',
        key: 'print22',
        src: 'img/img22.jpg',
        location: 'Tromsø, Norway',
        date: 'January 2009',
        basePrice: 65
    },
    {
        id: 'XXI',
        key: 'print14',
        src: 'img/img14.jpg',
        location: 'Tromsø, Norway',
        date: 'January 2009',
        basePrice: 65
    }
];
