const bascule = svgmap.bascule_side_groep.node;
const landhoofd_noord = svgmap.landhoofd_noord.node;
const landhoofd_zuid = svgmap.landhoofd_zuid.node;
const pijler6 = svgmap.pijler6_compleet_groep.node;
const pijler5 = svgmap.pijler5_groep.node;
const pijler4 = svgmap.pijler4_compleet_groep.node;
const aanbrug = svgmap.aanbrug_compleet_groep.node;
const assenstelsel = svgmap.assenstelsel_groep.node;
const bridge_element = data.series[0].fields.find(f => f.name === "Name")?.values?.get(0) ?? "Pijler1";

const hoofd_rotatie = svgmap.hoofd_compleet_groep.node;
const voorhar_rotatie = svgmap.voorhar_compleet_groep.node;
const brug_rotatie = svgmap.brug_compleet_groep.node;
const neven_rotatie = svgmap.neven_compleet_groep.node;
const rotatiey_pijl = svgmap.rotatiey_pijl.node;

// Lists of bridge elements
const pijler4list = ["Pijler4"];
const pijler5list = ["Pijler5"];
const pijler6list = ["Pijler6"];
const aanbruglist = ["Pijler1", "Pijler2", "Pijler3", "Pijler7", "Pijler8", "Pijler9"];
const basculelist = ["Basculekelder"];
const landhoofdzuidlist = ["LandhoofdZuid"];
const landhoofdnoordlist = ["LandhoofdNoord"];

//Hoofdoplegging koppelings waarde & variabele
const hoofdoplegging_rotatiey = svgmap.hoofdoplegging_value_label.node;
const hoofdoplegging_rotatiey_raw = data.series[0].fields.find(f => f.name === "Hoofd_rotatiey")?.values?.get(0) ?? 0;
//const hoofdoplegging_rotatiey_value = Number(hoofdoplegging_rotatiey_raw.toFixed(2));

//Brugoplegging koppelings waarde & variabele
const brugoplegging_rotatiey = svgmap.brug_value_label.node;
const brugoplegging_rotatiey_raw = data.series[0].fields.find(f => f.name === "Brug_rotatiey")?.values?.get(0) ?? 0;

//Nevenoplegging koppelings waarde & variabele
const nevenoplegging_rotatiey = svgmap.neven_value_label.node;
const nevenoplegging_rotatiey_raw = data.series[0].fields.find(f => f.name === "Neven_rotatiey")?.values?.get(0) ?? 0;

//Voorharoplegging koppelings waarde & variabele
const voorharoplegging_rotatiey = svgmap.Voorhar_value_label.node;
const voorharoplegging_rotatiey_raw = data.series[0].fields.find(f => f.name === "Voorhar_rotatiey")?.values?.get(0) ?? 0;

//Landhoofdbascule koppelings waarde & variabele
const landhoofd_rotatiey = svgmap.landhoofd_rotatie_value_label.node;
const landhoofd_rotatiey_raw = data.series[0].fields.find(f => f.name === "Brug_rotatiey")?.values?.get(0) ?? 0;

// Reset all to hidden first (optional, makes logic simpler)
pijler6.setAttribute("visibility", "hidden");
pijler5.setAttribute("visibility", "hidden");
pijler4.setAttribute("visibility", "hidden");
aanbrug.setAttribute("visibility", "hidden");
bascule.setAttribute("visibility", "hidden");
landhoofd_noord.setAttribute("visibility", "hidden");
landhoofd_zuid.setAttribute("visibility", "hidden");
landhoofd_rotatiey.setAttribute("visibility", "hidden")
rotatiey_pijl.setAttribute("visibility", "hidden");

hoofd_rotatie.setAttribute("visibility", "hidden");
voorhar_rotatie.setAttribute("visibility", "hidden");
brug_rotatie.setAttribute("visibility", "hidden");
neven_rotatie.setAttribute("visibility", "hidden");

// Show the correct one
if (pijler6list.includes(bridge_element)) {
    pijler6.setAttribute("visibility", "visible");
    hoofd_rotatie.setAttribute("visibility", "visible");
    neven_rotatie.setAttribute("visibility", "visible");
    voorhar_rotatie.setAttribute("visibility", "visible");

    assenstelsel.setAttribute("transform", "translate(-100,-100)");
    hoofd_rotatie.setAttribute("transform", "translate(-100,-80)");
    neven_rotatie.setAttribute("transform", "translate(-100,-80)");
    voorhar_rotatie.setAttribute("transform", "translate(-100,-80)");

    const hoofdoplegging_rotatiey_value = Number(hoofdoplegging_rotatiey_raw.toFixed(2));
    hoofdoplegging_rotatiey.textContent = hoofdoplegging_rotatiey_value + " mm";
    const nevenoplegging_rotatiey_value = Number(nevenoplegging_rotatiey_raw.toFixed(2));
    nevenoplegging_rotatiey.textContent = nevenoplegging_rotatiey_value + " mm";
    const voorharoplegging_rotatiey_value = Number(voorharoplegging_rotatiey_raw.toFixed(2));
    voorharoplegging_rotatiey.textContent = voorharoplegging_rotatiey_value + " mm";


} else if (pijler5list.includes(bridge_element)) {
    pijler5.setAttribute("visibility", "visible");
    hoofd_rotatie.setAttribute("visibility", "visible");

    assenstelsel.setAttribute("transform", "translate(-110,-100)");
    hoofd_rotatie.setAttribute("transform", "translate(0,-130)");

    const hoofdoplegging_rotatiey_value = Number(hoofdoplegging_rotatiey_raw.toFixed(2));
    hoofdoplegging_rotatiey.textContent = hoofdoplegging_rotatiey_value + " mm";

} else if (pijler4list.includes(bridge_element)) {
    hoofd_rotatie.setAttribute("visibility", "visible");
    brug_rotatie.setAttribute("visibility", "visible");
    neven_rotatie.setAttribute("visibility", "visible");
    pijler4.setAttribute("visibility", "visible");

    assenstelsel.setAttribute("transform", "translate(-110,-100)");
    hoofd_rotatie.setAttribute("transform", "translate(110,-80)");
    brug_rotatie.setAttribute("transform", "translate(-100,-110)");
    neven_rotatie.setAttribute("transform", "translate(-90, -90)");

    
    //Connect the calculated oplegging values from the database to the visualization
    hoofdoplegging_rotatiey.textContent = "N/A";
    brugoplegging_rotatiey.textContent = "N/A";
    nevenoplegging_rotatiey.textContent = "N/A";

} else if (aanbruglist.includes(bridge_element)) {
    aanbrug.setAttribute("visibility", "visible");
    brug_rotatie.setAttribute("visibility", "visible");

    assenstelsel.setAttribute("transform", "translate(-100,-100)");
    brug_rotatie.setAttribute("transform", "translate(0,-130)");

    if (bridge_element != "Pijler8"){
    const brugoplegging_rotatiey_value = Number(brugoplegging_rotatiey_raw.toFixed(2));
    brugoplegging_rotatiey.textContent = brugoplegging_rotatiey_value + " mm";
    }
    else{
    brugoplegging_rotatiey.textContent = "N/A";
    }

} else if (basculelist.includes(bridge_element)) {
    bascule.setAttribute("visibility", "visible");
    landhoofd_rotatiey.setAttribute("visibility", "visible");
    const landhoofd_rotatiey_value = Number(landhoofd_rotatiey_raw.toFixed(2));
    landhoofd_rotatiey.textContent = landhoofd_rotatiey_value + " mm";

    assenstelsel.setAttribute("transform", "translate(-115,100)");
}
else if (landhoofdzuidlist.includes(bridge_element)) {

    landhoofd_zuid.setAttribute("visibility", "visible")
    assenstelsel.setAttribute("transform", "translate(-50,50)");
    landhoofd_rotatiey.setAttribute("visibility", "visible");
    const landhoofd_rotatiey_value = Number(landhoofd_rotatiey_raw.toFixed(2));
    landhoofd_rotatiey.textContent = landhoofd_rotatiey_value + " mm";
}
else if (landhoofdnoordlist.includes(bridge_element)) {

    landhoofd_noord.setAttribute("visibility", "visible");
    assenstelsel.setAttribute("transform", "translate(-150,30)");

    landhoofd_rotatiey.setAttribute("visibility", "visible");
    const landhoofd_rotatiey_value = Number(landhoofd_rotatiey_raw.toFixed(2));
    landhoofd_rotatiey.textContent = landhoofd_rotatiey_value + " mm";
}
