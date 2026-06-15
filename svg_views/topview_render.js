const topview_rect = svgmap.top_rect_groep.node; 
const topview_oval = svgmap.top_oval_groep.node;

const oplegging1_basc = svgmap.oplegging1_basc_groep.node;
const oplegging2_basc = svgmap.oplegging2_basc_groep.node;
const oplegging_pijler4 = svgmap.oplegging_pijler4.node;
const oplegging_pijler6 = svgmap.oplegging_pijler6.node;
const oplegging_pijler5 = svgmap.oplegging_pijler5.node;
const oplegging_aanbrug = svgmap.oplegging_aanbruggen.node;
const oplegging_landhoofdnoord = svgmap.oplegging_landhoofdnoord.node;
const oplegging_landhoofdzuid = svgmap.oplegging_landhoofdzuid.node;
const assenstelsel = svgmap.assenstelsel_groep.node;
const compleety = svgmap.verplaatsingy_compleet.node;

const oplegging1_verplaatsingx_groep = svgmap.oplegging1_verplaatsingx_textgroep.node;
const oplegging2_verplaatsingx_groep = svgmap.oplegging2_verplaatsingx_textgroep.node;
const pijler4_brugoplegging_text_west = svgmap.pijler4_brugtext_west_compleet.node;
const pijler4_brugoplegging_text_oost = svgmap.pijler4_brugtext_oost_compleet.node;
const pijler4_nevenhoofdtext_oost_compleet = svgmap.pijler4_nevenhoofdtext_oost_compleet.node;
const pijler4_nevenhoofdtext_west_compleet = svgmap.pijler4_nevenhoofdtext_west_compleet.node;

const hoofdpijlerlist = ["Pijler5"];
const pijler4list = ["Pijler4"]
const pijler6list = ["Pijler6"]
const aanbruglist = ["Pijler1", "Pijler2", "Pijler3", "Pijler7", "Pijler8", "Pijler9"];
const basculelist = ["Basculekelder"];
const landhoofdnoordlist = ["LandhoofdNoord"];
const landhoofdzuidlist = ["LandhoofdZuid"];

const verplaatsing_opl1 = svgmap.verplaatsingx_opl1_value_label.node;
const verplaatsing_opl2 = svgmap.verplaatsingx_opl2_value_label.node;
const verplaatsingy = svgmap.verplaatsingy_value_label.node;
const verplaatsing_brugopl1_pijler4 = svgmap.brug_rotatie_west_label.node;
const verplaatsing_brugopl2_pijler4 = svgmap.brug_rotatie_oost_label.node;
const verplaatsing_hoofdopl1_pijler4 = svgmap.pijler4_rotatieneven_west_label.node;
const verplaatsing_hoofdopl2_pijler4 = svgmap.pijler4_rotatieneven_oost_label.node;
const verplaatsing_object = svgmap.object_verplaatsing_y_label.node;
const rotatiez = svgmap.rotatiez_label.node;
const rotatiez_text = svgmap.rotatieztext_label.node;
rotatiez_text.textContent = "Rotatie om de Z-as tussen opleggingen (+ met de klok mee)"

const brug_opleg_afstand = data.series[0].fields.find(f => f.name === "Brug_opleg_dist")?.values?.get(0) ?? 0;
const hoofd_opleg_afstand = data.series[0].fields.find(f => f.name === "Hoofd_opleg_dist")?.values?.get(0) ?? 0;
const neven_opleg_afstand = data.series[0].fields.find(f => f.name === "Neven_opleg_dist")?.values?.get(0) ?? 0;
const voorhar_opleg_afstand = data.series[0].fields.find(f => f.name === "Voorhar_opleg_dist")?.values?.get(0) ?? 0;
const afstand_oplegging = svgmap.afstand_oplegging_value_label.node;
const afstand_oplegging_text = svgmap.afstand_oplegging_text_label.node;
afstand_oplegging_text.textContent = "Afstand opleggingen"
afstand_oplegging_text.removeAttribute("transform")

const oplegging1_text = svgmap.oplegging1_text_label.node;
const oplegging2_text = svgmap.oplegging2_text_label.node;
const verplaatsing_text_opl1 = svgmap.verplaatsingx_opl1_text_label.node;
const verplaatsing_text_opl2 = svgmap.verplaatsingx_opl2_text_label.node;
const bridge_element = data.series[0].fields.find(f => f.name === "Name")?.values?.get(0) ?? "Pijler1"

const verplaatsingx_brug_opl1_value_raw = data.series[0].fields.find(f => f.name === "Brugpunt1_deltax")?.values?.get(0) ?? 0
const verplaatsingx_brug_opl2_value_raw = data.series[0].fields.find(f => f.name === "Brugpunt2_deltax")?.values?.get(0) ?? 0
const verplaatsingx_hoofd_opl1_value_raw = data.series[0].fields.find(f => f.name === "Hoofdpunt1_deltax")?.values?.get(0) ?? 0
const verplaatsingx_hoofd_opl2_value_raw = data.series[0].fields.find(f => f.name === "Hoofdpunt2_deltax")?.values?.get(0) ?? 0


const verplaatsingy_value_raw = data.series[0].fields.find(f => f.name === "delta_y")?.values?.get(0) ?? 0
const verplaatsingy_value = Number(verplaatsingy_value_raw.toFixed(2));

const rotatiez_brugvalue_raw = data.series[0].fields.find(f => f.name === "Brug_rotatiez")?.values?.get(0) ?? 0
const rotatiez_hoofdvalue_raw = data.series[0].fields.find(f => f.name === "Hoofd_rotatiez")?.values?.get(0) ?? 0



oplegging1_verplaatsingx_groep.setAttribute("visibility", "visible")
oplegging2_verplaatsingx_groep.setAttribute("visibility", "visible")
rotatiez.setAttribute("visibility", "visible")
pijler4_brugoplegging_text_west.setAttribute("visibility", "hidden")
pijler4_brugoplegging_text_oost.setAttribute("visibility", "hidden")
pijler4_nevenhoofdtext_oost_compleet.setAttribute("visibility", "hidden")
pijler4_nevenhoofdtext_west_compleet.setAttribute("visibility", "hidden")
afstand_oplegging.setAttribute("visibility", "visible")

topview_oval.setAttribute("visibility", "hidden");
topview_rect.setAttribute("visibility", "hidden");
oplegging1_basc.setAttribute("visibility", "hidden");
oplegging2_basc.setAttribute("visibility", "hidden");
oplegging_pijler5.setAttribute("visibility", "hidden");
oplegging_pijler6.setAttribute("visibility", "hidden");
oplegging_aanbrug.setAttribute("visibility", "hidden");
oplegging_pijler4.setAttribute("visibility", "hidden");
oplegging_landhoofdzuid.setAttribute("visibility", "hidden");
oplegging_landhoofdnoord.setAttribute("visibility", "hidden");

// Hide element if it's not in the list
if (hoofdpijlerlist.includes(bridge_element)) {
    topview_oval.setAttribute("visibility", "visible");
    oplegging_pijler5.setAttribute("visibility", "visible");
    oplegging_pijler5.setAttribute("transform", "translate(-20,0)")

    oplegging1_text.setAttribute("x", 380);
    oplegging1_text.setAttribute("y",95);
    verplaatsing_text_opl1.setAttribute("x", 380);
    verplaatsing_text_opl1.setAttribute("y", 120);
    verplaatsing_opl1.setAttribute("x", 380);
    verplaatsing_opl1.setAttribute("y", 145);
    oplegging1_verplaatsingx_groep.setAttribute("transform", "translate(-20,125)")
    oplegging2_verplaatsingx_groep.setAttribute("transform", "translate(-20,125)")

    oplegging2_text.setAttribute("x", 880);
    oplegging2_text.setAttribute("y", 100);
    verplaatsing_text_opl2.setAttribute("x", 880);
    verplaatsing_text_opl2.setAttribute("y", 125);
    verplaatsing_opl2.setAttribute("x", 880);
    verplaatsing_opl2.setAttribute("y", 150);

    assenstelsel.removeAttribute("transform")
    compleety.setAttribute("transform", "translate(-10,0)")

    const verplaatsingx_hoofd_opl1_value = Number(verplaatsingx_hoofd_opl1_value_raw.toFixed(2));
    verplaatsing_opl1.textContent = verplaatsingx_hoofd_opl1_value + " mm";
    const verplaatsingx_hoofd_opl2_value = Number(verplaatsingx_hoofd_opl2_value_raw.toFixed(2));
    verplaatsing_opl2.textContent = verplaatsingx_hoofd_opl2_value + " mm";

    const rotatiez_value = Number(rotatiez_hoofdvalue_raw.toFixed(2));
    rotatiez.textContent = rotatiez_value + " mm"

    afstand_oplegging.textContent = hoofd_opleg_afstand + " m"
}
else if (pijler6list.includes(bridge_element)) {
    topview_oval.setAttribute("visibility", "visible");
    topview_rect.setAttribute("visibility", "hidden");
    oplegging_pijler6.setAttribute("visibility", "visible");

    afstand_oplegging.textContent = hoofd_opleg_afstand + " m"
    oplegging_pijler5.setAttribute("transform", "translate(-20,0)")

    oplegging1_text.setAttribute("x", 400);
    oplegging1_text.setAttribute("y",105);
    verplaatsing_text_opl1.setAttribute("x", 400);
    verplaatsing_text_opl1.setAttribute("y", 130);
    verplaatsing_opl1.setAttribute("x", 400);
    verplaatsing_opl1.setAttribute("y", 155);
    oplegging1_verplaatsingx_groep.setAttribute("transform", "translate(-20,125)")
    oplegging2_verplaatsingx_groep.setAttribute("transform", "translate(-20,125)")

    oplegging2_text.setAttribute("x", 865);
    oplegging2_text.setAttribute("y", 105);
    verplaatsing_text_opl2.setAttribute("x", 865);
    verplaatsing_text_opl2.setAttribute("y", 130);
    verplaatsing_opl2.setAttribute("x", 865);
    verplaatsing_opl2.setAttribute("y", 155);

    assenstelsel.removeAttribute("transform")
    compleety.setAttribute("transform", "translate(-10,0)")

    const verplaatsingx_hoofd_opl1_value = Number(verplaatsingx_hoofd_opl1_value_raw.toFixed(2));
    verplaatsing_opl1.textContent = verplaatsingx_hoofd_opl1_value + " mm";
    const verplaatsingx_hoofd_opl2_value = Number(verplaatsingx_hoofd_opl2_value_raw.toFixed(2));
    verplaatsing_opl2.textContent = verplaatsingx_hoofd_opl2_value + " mm";
    
    const rotatiez_value = Number(rotatiez_hoofdvalue_raw.toFixed(2));
    rotatiez.textContent = rotatiez_value + " mm"
}
else if (basculelist.includes(bridge_element)) {
    topview_rect.setAttribute("visibility", "visible");
    oplegging1_basc.setAttribute("visibility", "visible");
    oplegging2_basc.setAttribute("visibility", "visible");
    afstand_oplegging.textContent = brug_opleg_afstand + " m"

    oplegging1_text.setAttribute("x", 380);
    oplegging1_text.setAttribute("y",95);
    verplaatsing_text_opl1.setAttribute("x", 380);
    verplaatsing_text_opl1.setAttribute("y", 120);
    verplaatsing_opl1.setAttribute("x", 380);
    verplaatsing_opl1.setAttribute("y", 145);

    oplegging2_text.setAttribute("x", 880);
    oplegging2_text.setAttribute("y", 100);
    verplaatsing_text_opl2.setAttribute("x", 880);
    verplaatsing_text_opl2.setAttribute("y", 125);
    verplaatsing_opl2.setAttribute("x", 880);
    verplaatsing_opl2.setAttribute("y", 150);

    oplegging1_verplaatsingx_groep.removeAttribute("transform")
    oplegging2_verplaatsingx_groep.removeAttribute("transform")

    const verplaatsingx_brug_opl1_value = Number(verplaatsingx_brug_opl1_value_raw.toFixed(2));
    verplaatsing_opl1.textContent = verplaatsingx_brug_opl1_value + " mm";
    const verplaatsingx_brug_opl2_value = Number(verplaatsingx_brug_opl2_value_raw.toFixed(2));
    verplaatsing_opl2.textContent = verplaatsingx_brug_opl2_value + " mm";

    const rotatiez_value = Number(rotatiez_brugvalue_raw.toFixed(2));
    rotatiez.textContent = rotatiez_value + " mm"
}
else if (aanbruglist.includes(bridge_element)) {
    topview_oval.setAttribute("visibility", "visible");
    oplegging_aanbrug.setAttribute("visibility", "visible");
    afstand_oplegging.textContent = brug_opleg_afstand + " m"
    afstand_oplegging.setAttribute("transform", "translate(10,0)")

    oplegging1_text.setAttribute("x", 180);
    oplegging1_text.setAttribute("y", 217.5);
    verplaatsing_text_opl1.setAttribute("x", 180);
    verplaatsing_text_opl1.setAttribute("y", 242.5);
    verplaatsing_opl1.setAttribute("x", 180);
    verplaatsing_opl1.setAttribute("y", 267.5);

    oplegging2_text.setAttribute("x", 1045);
    oplegging2_text.setAttribute("y", 217.5);
    verplaatsing_text_opl2.setAttribute("x", 1045);
    verplaatsing_text_opl2.setAttribute("y", 242.5);
    verplaatsing_opl2.setAttribute("x", 1045);
    verplaatsing_opl2.setAttribute("y", 267.5);

    oplegging1_verplaatsingx_groep.removeAttribute("transform")
    oplegging2_verplaatsingx_groep.removeAttribute("transform")

    const verplaatsingx_brug_opl1_value = Number(verplaatsingx_brug_opl1_value_raw.toFixed(2));
    verplaatsing_opl1.textContent = verplaatsingx_brug_opl1_value + " mm";
    const verplaatsingx_brug_opl2_value = Number(verplaatsingx_brug_opl2_value_raw.toFixed(2));
    verplaatsing_opl2.textContent = verplaatsingx_brug_opl2_value + " mm";
    
    const rotatiez_value = Number(rotatiez_brugvalue_raw.toFixed(2));
    rotatiez.textContent = rotatiez_value + " mm"
}
else if (pijler4list.includes(bridge_element)) {
    topview_oval.setAttribute("visibility", "visible");
    oplegging_pijler4.setAttribute("visibility", "visible");
    afstand_oplegging.textContent = "23.9 m"

    oplegging1_text.setAttribute("x", 275);
    oplegging1_text.setAttribute("y", 217.5);
    verplaatsing_text_opl1.setAttribute("x", 275);
    verplaatsing_text_opl1.setAttribute("y", 242.5);
    verplaatsing_opl1.setAttribute("x", 275);
    verplaatsing_opl1.setAttribute("y", 267.5);

    oplegging1_verplaatsingx_groep.setAttribute("visibility", "hidden")
    oplegging2_verplaatsingx_groep.setAttribute("visibility", "hidden")
    pijler4_brugoplegging_text_west.setAttribute("visibility", "visible")
    pijler4_brugoplegging_text_oost.setAttribute("visibility", "visible")
    pijler4_nevenhoofdtext_oost_compleet.setAttribute("visibility", "visible")
    pijler4_nevenhoofdtext_west_compleet.setAttribute("visibility", "visible")
    rotatiez.setAttribute("visibility", "hidden")

    oplegging2_text.setAttribute("x", 950);
    oplegging2_text.setAttribute("y", 217.5);
    verplaatsing_text_opl2.setAttribute("x", 950);
    verplaatsing_text_opl2.setAttribute("y", 242.5);
    verplaatsing_opl2.setAttribute("x", 950);
    verplaatsing_opl2.setAttribute("y", 267.5);

    assenstelsel.setAttribute("transform", "translate(5, 30)")
    compleety.setAttribute("transform", "translate(-20, 0)")
    verplaatsingx_hoofd_opl1_value_raw
    const verplaatsingx_brug_opl1_value = Number(verplaatsingx_brug_opl1_value_raw.toFixed(2));
    verplaatsing_brugopl1_pijler4.textContent = verplaatsingx_brug_opl1_value + " mm";
    const verplaatsingx_brug_opl2_value = Number(verplaatsingx_brug_opl2_value_raw.toFixed(2));
    verplaatsing_brugopl2_pijler4.textContent = verplaatsingx_brug_opl2_value + " mm";
    const verplaatsingx_hoofd_opl1_value = Number(verplaatsingx_hoofd_opl1_value_raw.toFixed(2));
    verplaatsing_hoofdopl1_pijler4.textContent = verplaatsingx_hoofd_opl1_value + " mm" 
    const verplaatsingx_hoofd_opl2_value = Number(verplaatsingx_hoofd_opl2_value_raw.toFixed(2));
    verplaatsing_hoofdopl2_pijler4.textContent = verplaatsingx_hoofd_opl2_value + " mm"

    afstand_oplegging.setAttribute("visibility", "hidden")
    afstand_oplegging_text.setAttribute("transform", "translate(15,0)")
    afstand_oplegging_text.textContent = "Afstand opleggingen " + hoofd_opleg_afstand + " m" + " & " + brug_opleg_afstand + " m"
    const rotatiez_brugvalue = Number(rotatiez_brugvalue_raw.toFixed(2));
    const rotatiez_hoofdvalue = Number(rotatiez_hoofdvalue_raw.toFixed(2));
    rotatiez_text.textContent = "Rotatie om de Z-as (+ met de klok mee) tussen Brug opleggingen " + rotatiez_brugvalue + " mm" + " & hoofd opleggingen " + rotatiez_hoofdvalue + " mm"
}
else if (landhoofdnoordlist.includes(bridge_element)) {
    topview_oval.setAttribute("visibility", "visible");
    oplegging_landhoofdnoord.setAttribute("visibility", "visible");
    afstand_oplegging.textContent = brug_opleg_afstand + " m"

    oplegging1_text.setAttribute("x", 180);
    oplegging1_text.setAttribute("y", 217.5);
    verplaatsing_text_opl1.setAttribute("x", 180);
    verplaatsing_text_opl1.setAttribute("y", 242.5);
    verplaatsing_opl1.setAttribute("x", 180);
    verplaatsing_opl1.setAttribute("y", 267.5);

    oplegging2_text.setAttribute("x", 1045);
    oplegging2_text.setAttribute("y", 217.5);
    verplaatsing_text_opl2.setAttribute("x", 1045);
    verplaatsing_text_opl2.setAttribute("y", 242.5);
    verplaatsing_opl2.setAttribute("x", 1045);
    verplaatsing_opl2.setAttribute("y", 267.5);

    oplegging1_verplaatsingx_groep.removeAttribute("transform")
    oplegging2_verplaatsingx_groep.removeAttribute("transform")

    const verplaatsingx_brug_opl1_value = Number(verplaatsingx_brug_opl1_value_raw.toFixed(2));
    verplaatsing_opl1.textContent = verplaatsingx_brug_opl1_value + " mm";
    const verplaatsingx_brug_opl2_value = Number(verplaatsingx_brug_opl2_value_raw.toFixed(2));
    verplaatsing_opl2.textContent = verplaatsingx_brug_opl2_value + " mm";

    const rotatiez_value = Number(rotatiez_brugvalue_raw.toFixed(2));
    rotatiez.textContent = rotatiez_value + " mm"
}
else if (landhoofdzuidlist.includes(bridge_element)) {
    topview_oval.setAttribute("visibility", "visible");
    oplegging_landhoofdzuid.setAttribute("visibility", "visible");
    afstand_oplegging.textContent = brug_opleg_afstand + " m"

    oplegging1_text.setAttribute("x", 180);
    oplegging1_text.setAttribute("y", 217.5);
    verplaatsing_text_opl1.setAttribute("x", 180);
    verplaatsing_text_opl1.setAttribute("y", 242.5);
    verplaatsing_opl1.setAttribute("x", 180);
    verplaatsing_opl1.setAttribute("y", 267.5);

    oplegging2_text.setAttribute("x", 1045);
    oplegging2_text.setAttribute("y", 217.5);
    verplaatsing_text_opl2.setAttribute("x", 1045);
    verplaatsing_text_opl2.setAttribute("y", 242.5);
    verplaatsing_opl2.setAttribute("x", 1045);
    verplaatsing_opl2.setAttribute("y", 267.5);

    oplegging1_verplaatsingx_groep.removeAttribute("transform")
    oplegging2_verplaatsingx_groep.removeAttribute("transform")

    const verplaatsingx_brug_opl1_value = Number(verplaatsingx_brug_opl1_value_raw.toFixed(2));
    verplaatsing_opl1.textContent = verplaatsingx_brug_opl1_value + " mm";
    const verplaatsingx_brug_opl2_value = Number(verplaatsingx_brug_opl2_value_raw.toFixed(2));
    verplaatsing_opl2.textContent = verplaatsingx_brug_opl2_value + " mm";

    const rotatiez_value = Number(rotatiez_brugvalue_raw.toFixed(2));
    rotatiez.textContent = rotatiez_value + " mm"
}

// Display text

verplaatsingy.textContent = verplaatsingy_value + " mm";
verplaatsing_object.textContent = bridge_element;
