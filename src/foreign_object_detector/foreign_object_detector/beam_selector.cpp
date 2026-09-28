// Точный выбор соседних лучей по замороженным углам с резервным расчетом NumPy.
#include <cstddef>
#include <cmath>
extern "C" void rescue_beam_select(const double* e, std::size_t n,
                                   const double* beams, unsigned char* off) {
    for (std::size_t i=0; i<n; ++i) {
        std::size_t lo=0, hi=128;
        while (lo<hi) {const auto m=(lo+hi)/2; if (beams[m]<e[i]) lo=m+1; else hi=m;}
        std::size_t j=lo<1 ? 1 : (lo>127 ? 127 : lo);
        if (std::abs(e[i]-beams[j-1])<=std::abs(e[i]-beams[j])) --j;
        off[i]=std::abs(e[i]-beams[j])>0.02;
    }
}
// В неоднозначной окрестности границы используем исходные операции NumPy:
// hypot/atan2/degrees и выбор ближайшего луча, сохраняя исходную арифметику.
extern "C" void rescue_beam_screen(const double* p, std::size_t n,
    const double* tangent, const double* inner_lo, const double* inner_hi,
    const double* outer_lo, const double* outer_hi, const int* lookup, unsigned char* codes) {
    for (std::size_t i=0;i<n;++i) {
        const double x=p[3*i],y=p[3*i+1],z=p[3*i+2];codes[i]=0;
        if (!(x<60) || !std::isfinite(x) || !std::isfinite(y) || !std::isfinite(z)
            || (x==0 && y==0 && z==0)) continue;
        // Ограничиваем область обычными конечными величинами.
        const double scale=std::fmax(std::abs(x),std::fmax(std::abs(y),std::abs(z)));
        if (scale>1e100 || scale<1e-100) {codes[i]=2;continue;}
        const double h=std::sqrt(x*x+y*y);
        if (h<1e-100) {codes[i]=2;continue;}
        const double r=z/h;
        std::size_t lo;
        if (r<=tangent[0]) lo=0;
        else if(r>tangent[127]) lo=128;
        else {
            int cell=static_cast<int>((r-tangent[0])*(4096.0/(tangent[127]-tangent[0])));
            if(cell<0)cell=0;if(cell>4095)cell=4095;
            lo=static_cast<std::size_t>(lookup[cell]);
            while(lo>0 && !(tangent[lo-1]<r)) --lo;
            while(lo<128 && tangent[lo]<r) ++lo;
        }
        const std::size_t a=lo==0?0:lo-1,b=lo>=128?127:lo;
        const bool inside=(r>=inner_lo[a] && r<=inner_hi[a]) || (r>=inner_lo[b] && r<=inner_hi[b]);
        const bool outside=(r<outer_lo[a] || r>outer_hi[a]) && (r<outer_lo[b] || r>outer_hi[b]);
        codes[i]=inside?0:(outside?1:2);
    }
}
